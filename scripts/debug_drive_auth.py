
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append('/Users/user/Github/ai-file-organizer')

try:
    from google_drive_auth import GoogleDriveAuth
    
    print("Testing Google Drive Authentication...")
    
    config_dir = Path.home() / ".ai_organizer_config"
    auth = GoogleDriveAuth(config_dir=config_dir)
    
    print(f"Config dir: {config_dir}")
    print(f"Credentials exist: {(config_dir / 'credentials.json').exists()}")
    print(f"Token exists: {(config_dir / 'token.json').exists()}")
    
    result = auth.test_authentication()
    
    print("\nAuthentication Result:")
    print(result)
    
    if result.get('success'):
        print("\n✅ Authentication Successful!")
    else:
        print("\n❌ Authentication Failed!")
        print(f"Error: {result.get('error')}")

except Exception as e:
    print(f"\n❌ Script Error: {e}")
    import traceback
    traceback.print_exc()
