import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FileText,
    Clock,
    Search,
    RefreshCw,
    Terminal,
    ExternalLink,
    ChevronRight,
    Shield,
    Activity
} from 'lucide-react';
import { listFiles, getFileContent } from '../services/cloudService';
import { cn } from '../lib/utils';

// Bucket name for the Bloom project audits
const AUDIT_BUCKET = 'veo-prompt-machine';

interface GCSFile {
    name: string;
    updated: string;
    size: string;
    contentType: string;
}

export default function ForensicVault() {
    const [files, setFiles] = useState<GCSFile[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [fileContent, setFileContent] = useState<string | null>(null);
    const [fetchingContent, setFetchingContent] = useState(false);
    const [accessToken, setAccessToken] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Fetch GCS access token from backend
    useEffect(() => {
        const fetchToken = async () => {
            try {
                const response = await fetch('/api/auth/token');
                if (!response.ok) {
                    throw new Error('Authentication required. Go to settings to reconnect Google Drive.');
                }
                const data = await response.json();
                setAccessToken(data.access_token);
            } catch (err: any) {
                setError(err.message);
            }
        };

        fetchToken();
    }, []);

    // Load files when token is available
    useEffect(() => {
        if (accessToken) {
            loadFiles();
        }
    }, [accessToken]);

    const loadFiles = async () => {
        if (!accessToken) return;
        setLoading(true);
        setError(null);
        try {
            const items = await listFiles(accessToken, AUDIT_BUCKET);
            // Sort by updated date descending
            const sorted = items.sort((a: any, b: any) => new Date(b.updated).getTime() - new Date(a.updated).getTime());
            setFiles(sorted);
        } catch (e: any) {
            console.error("Failed to list files:", e);
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleFileClick = async (fileName: string) => {
        if (!accessToken) return;
        setSelectedFile(fileName);
        setFetchingContent(true);
        try {
            const content = await getFileContent(fileName, accessToken, AUDIT_BUCKET);
            setFileContent(content);
        } catch (e) {
            setFileContent("Error loading file content.");
        } finally {
            setFetchingContent(false);
        }
    };

    const filteredFiles = files.filter(f =>
        f.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (error && !files.length) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                <Shield size={64} className="text-red-500/50 mb-6" />
                <h2 className="text-2xl font-bold text-white mb-2">Vault Access Restricted</h2>
                <p className="text-white/60 max-w-md mb-8">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary/80 transition-all font-medium"
                >
                    Check Authentication
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full overflow-hidden">
            {/* Header */}
            <header className="px-8 py-6 border-b border-white/10 flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <div className="p-2 bg-primary/20 rounded-lg">
                            <Shield size={20} className="text-primary" />
                        </div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Forensic Vault</h1>
                    </div>
                    <p className="text-sm text-white/40">
                        Private neural audit archives • <span className="text-primary/60 font-mono text-xs">{AUDIT_BUCKET}</span>
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={loadFiles}
                        className="p-2.5 bg-white/5 border border-white/10 rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all"
                        title="Refresh Manifest"
                    >
                        <RefreshCw size={18} className={cn(loading && "animate-spin")} />
                    </button>
                </div>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Sidebar: File List */}
                <div className="w-80 border-r border-white/10 flex flex-col bg-black/20">
                    <div className="p-4 border-b border-white/5">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                            <input
                                type="text"
                                placeholder="Search audit logs..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-primary/50 transition-all"
                            />
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                                <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                                <p className="text-xs text-white/40 uppercase tracking-widest font-bold">Scanning Vault...</p>
                            </div>
                        ) : filteredFiles.length === 0 ? (
                            <div className="text-center py-20 px-4">
                                <Activity size={32} className="mx-auto text-white/10 mb-4" />
                                <p className="text-white/40 text-xs font-medium">No records found matching search</p>
                            </div>
                        ) : (
                            filteredFiles.map((file) => (
                                <button
                                    key={file.name}
                                    onClick={() => handleFileClick(file.name)}
                                    className={cn(
                                        "w-full text-left p-3 rounded-xl transition-all border group",
                                        selectedFile === file.name
                                            ? 'bg-primary border-primary shadow-lg shadow-primary/20'
                                            : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/10'
                                    )}
                                >
                                    <div className="flex items-start gap-3">
                                        <div className={cn(
                                            "p-2 rounded-lg shrink-0",
                                            selectedFile === file.name ? 'bg-white/20' : 'bg-white/5'
                                        )}>
                                            <FileText size={16} className={selectedFile === file.name ? 'text-white' : 'text-primary'} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h4 className={cn(
                                                "text-xs font-semibold truncate",
                                                selectedFile === file.name ? 'text-white' : 'text-white/80 group-hover:text-white'
                                            )}>
                                                {file.name}
                                            </h4>
                                            <div className={cn(
                                                "flex items-center gap-2 mt-1 text-[10px] font-mono opacity-50",
                                                selectedFile === file.name ? 'text-white/80' : 'text-white/40'
                                            )}>
                                                <span className="flex items-center gap-1">
                                                    <Clock size={10} />
                                                    {new Date(file.updated).toLocaleDateString()}
                                                </span>
                                                <span>{(parseInt(file.size) / 1024).toFixed(1)} KB</span>
                                            </div>
                                        </div>
                                        <ChevronRight size={14} className={cn(
                                            "mt-1",
                                            selectedFile === file.name ? 'text-white/60' : 'text-white/20'
                                        )} />
                                    </div>
                                </button>
                            ))
                        )}
                    </div>

                    <div className="p-4 border-t border-white/5 bg-black/40 text-[10px] text-white/30 font-mono uppercase tracking-wider flex justify-between">
                        <span>Manifest: {files.length}</span>
                        <span>Active Session</span>
                    </div>
                </div>

                {/* Main: Content Viewer */}
                <div className="flex-1 bg-black/40 relative overflow-hidden flex flex-col">
                    <AnimatePresence mode="wait">
                        {!selectedFile ? (
                            <motion.div
                                key="empty"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex-1 flex flex-col items-center justify-center p-12 text-center"
                            >
                                <div className="relative mb-8">
                                    <Terminal size={80} className="text-white/5" />
                                    <Activity size={32} className="absolute inset-0 m-auto text-primary/20 animate-pulse" />
                                </div>
                                <h3 className="text-xl font-bold text-white/50 mb-2 uppercase tracking-wide">Select Audit Case</h3>
                                <p className="text-sm text-white/30 max-w-xs mx-auto leading-relaxed">
                                    Neural audit logs are vaulted for forensic review. Select a manifest entry to retrieve the payload.
                                </p>
                            </motion.div>
                        ) : fetchingContent ? (
                            <motion.div
                                key="loading"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex-1 flex flex-col items-center justify-center p-12 text-center"
                            >
                                <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-6"></div>
                                <p className="text-sm text-primary animate-pulse font-mono tracking-widest uppercase">Decrypting Forensic Payload...</p>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="content"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex-1 overflow-y-auto custom-scrollbar flex flex-col"
                            >
                                <div className="sticky top-0 z-10 px-10 py-6 bg-black/60 backdrop-blur-md border-b border-white/5 flex items-center justify-between">
                                    <h2 className="text-lg font-bold text-white truncate pr-4">
                                        {selectedFile}
                                    </h2>
                                    <div className="flex gap-2">
                                        <a
                                            href={`https://storage.cloud.google.com/${AUDIT_BUCKET}/${selectedFile}`}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white/60 text-[10px] font-bold uppercase hover:bg-white/10 hover:text-white transition-all flex items-center gap-2"
                                        >
                                            <ExternalLink size={14} /> Native GCS
                                        </a>
                                    </div>
                                </div>

                                <div className="px-10 py-12 flex-1">
                                    <div className="max-w-4xl mx-auto">
                                        <div className="space-y-6 font-mono text-sm">
                                            {fileContent?.split('\n').map((line, i) => {
                                                // Simple Custom Markdown Parser for Forensic Theme
                                                if (line.startsWith('# ')) {
                                                    return (
                                                        <div key={i} className="pt-8 pb-4 mb-8 border-b border-white/10">
                                                            <h1 className="text-3xl font-black uppercase text-white tracking-tighter">
                                                                <span className="text-primary mr-4 opacity-50">#</span>
                                                                {line.substring(2)}
                                                            </h1>
                                                        </div>
                                                    );
                                                }
                                                if (line.startsWith('## ')) {
                                                    return (
                                                        <h2 key={i} className="text-xl font-bold uppercase text-primary mt-10 mb-4 flex items-center gap-3">
                                                            <div className="w-2 h-2 bg-primary animate-pulse rounded-full" />
                                                            {line.substring(3)}
                                                        </h2>
                                                    );
                                                }
                                                if (line.startsWith('### ')) {
                                                    return (
                                                        <h3 key={i} className="text-sm font-bold text-white/90 mt-8 mb-3 bg-white/5 px-3 py-1 rounded inline-block">
                                                            {line.substring(4)}
                                                        </h3>
                                                    );
                                                }
                                                if (line.startsWith('> ')) {
                                                    return (
                                                        <blockquote key={i} className="border-l-2 border-primary/50 bg-primary/5 p-6 my-6 rounded-r-xl italic text-white/60">
                                                            {line.substring(2)}
                                                        </blockquote>
                                                    );
                                                }
                                                if (line.includes('|')) {
                                                    // Table row
                                                    const cells = line.split('|').filter(s => s.trim() || s === ' ');
                                                    if (line.includes('---')) return <div key={i} className="h-px bg-white/10 my-1" />;
                                                    return (
                                                        <div key={i} className="grid grid-cols-4 gap-4 py-2 border-b border-white/5 text-[11px] hover:bg-white/2 transition-colors">
                                                            {cells.map((cell, ci) => (
                                                                <span key={ci} className={ci === 0 ? 'text-primary font-bold' : 'text-white/60'}>
                                                                    {cell.trim()}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    );
                                                }
                                                if (line.trim() === '') return <div key={i} className="h-4" />;

                                                return (
                                                    <p key={i} className="text-white/60 leading-relaxed">
                                                        {line}
                                                    </p>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>

                                <footer className="px-10 py-6 border-t border-white/5 bg-black/20 text-[10px] text-white/20 flex justify-between uppercase font-mono">
                                    <span>Vault Retrieval: Success</span>
                                    <span>End of Audit Payload</span>
                                </footer>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
