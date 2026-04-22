import asyncio
import os
import sys
import logging
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

# Try to import mcp, handle if not installed (though we just installed it)
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)

class ResolveService:
    """
    Service to communicate with DaVinci Resolve via the samuelgursky/davinci-resolve-mcp server.
    """
    def __init__(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.server_script = os.path.join(self.root_dir, "external", "davinci-resolve-mcp", "src", "resolve_mcp_server.py")
        self.python_exec = sys.executable
        self.session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._lock = asyncio.Lock()

    async def connect(self):
        """Initialize connection to the MCP server"""
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP library not installed. Please run pip install mcp[cli]")

        async with self._lock:
            if self.session:
                return

            # Check for Remote Powerhouse configuration
            remote_url = None
            try:
                from gdrive_integration import get_metadata_root
                config_path = get_metadata_root() / "config" / "hybrid_config.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        remote = config.get("remote_powerhouse", {})
                        if remote.get("enabled"):
                            svc = remote.get("services", {}).get("resolve_mcp", {})
                            svc_ip = svc.get("ip") or remote.get("ip")
                            if svc_ip:
                                remote_url = f"http://{svc_ip}:{svc.get('port', 8000)}{svc.get('endpoint', '/sse')}"
            except Exception as e:
                logger.warning(f"Failed to load hybrid config: {e}")

            if remote_url:
                logger.info(f"Connecting to REMOTE Resolve MCP Server at {remote_url}")
                try:
                    self._exit_stack = AsyncExitStack()
                    transport_read, transport_write = await self._exit_stack.enter_async_context(sse_client(remote_url))
                    self.session = await self._exit_stack.enter_async_context(ClientSession(transport_read, transport_write))
                    
                    await self.session.initialize()
                    logger.info("✅ Successfully connected to REMOTE DaVinci Resolve MCP Server")
                    return
                except Exception as e:
                    logger.error(f"❌ Failed to connect to REMOTE Resolve MCP: {e}")
                    # Fallback to local if remote fails? Or just raise?
                    # For now, let's fall back to local to avoid blocking if the 5090 is off.
                    logger.info("Falling back to local Resolve MCP connection...")

            logger.info(f"Connecting to LOCAL Resolve MCP Server at {self.server_script}")
            
            # Ensure Resolve paths are in environment
            env = os.environ.copy()
            if "RESOLVE_SCRIPT_API" not in env:
                env["RESOLVE_SCRIPT_API"] = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
            if "RESOLVE_SCRIPT_LIB" not in env:
                env["RESOLVE_SCRIPT_LIB"] = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
            
            # Set PYTHONPATH to include the src directory of the MCP server
            mcp_src_dir = os.path.dirname(self.server_script)
            env["PYTHONPATH"] = f"{env.get('PYTHONPATH', '')}:{mcp_src_dir}"

            server_params = StdioServerParameters(
                command=self.python_exec,
                args=[self.server_script],
                env=env
            )

            try:
                self._exit_stack = AsyncExitStack()
                transport_read, transport_write = await self._exit_stack.enter_async_context(stdio_client(server_params))
                self.session = await self._exit_stack.enter_async_context(ClientSession(transport_read, transport_write))
                
                await self.session.initialize()
                logger.info("✅ Successfully connected to DaVinci Resolve MCP Server")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Resolve MCP: {e}")
                if self._exit_stack:
                    await self._exit_stack.aclose()
                self.session = None
                self._exit_stack = None
                raise

    async def disconnect(self):
        """Shutdown the MCP server connection"""
        async with self._lock:
            if self._exit_stack:
                await self._exit_stack.aclose()
                self.session = None
                self._exit_stack = None
                logger.info("Disconnected from Resolve MCP Server")

    async def list_tools(self):
        """List available tools from the MCP server"""
        if not self.session:
            await self.connect()
        return await self.session.list_tools()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a specific tool on the MCP server"""
        if not self.session:
            await self.connect()
        
        logger.info(f"Calling Resolve tool: {tool_name} with args: {arguments}")
        try:
            result = await self.session.call_tool(tool_name, arguments or {})
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    # High-level helper methods
    async def get_version(self) -> str:
        res = await self.session.read_resource("resolve://version")
        return res.content[0].text if res.content else "Unknown"

    async def add_timeline_marker(self, frame: int, color: str = "Blue", note: str = ""):
        return await self.call_tool("add_marker", {"frame": frame, "color": color, "note": note})

    async def create_bin(self, name: str):
        return await self.call_tool("create_bin", {"name": name})

    async def import_media(self, path: str):
        return await self.call_tool("import_media", {"file_path": path})

# Global instance
resolve_instance = ResolveService()
