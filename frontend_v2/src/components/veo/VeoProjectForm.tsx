/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useRef, useState } from 'react';
import type { ProjectAsset } from '../../types/veo';
import { ArrowRightIcon, FileUploadIcon, FileAudioIcon, RectangleStackIcon, UploadCloudIcon } from './icons';
import AssetLibrary from './AssetLibrary';

interface VeoProjectFormProps {
    onGenerate: (script: string, createKeyframes: boolean) => void;
    isGenerating: boolean;
    onLoadProject: (jsonString: string) => void;
    onArchiveProject: (jsonString: string) => void;
    assets: ProjectAsset[];
    onAnalyzeScriptForAssets: (script: string) => void;
    isAnalyzingAssets: boolean;
    onAddAsset: (asset: ProjectAsset) => void;
    onRemoveAsset: (id: string) => void;
    onUpdateAssetImage: (id: string, file: File) => void;
}

const VeoProjectForm: React.FC<VeoProjectFormProps> = ({
    onGenerate, isGenerating, assets, onAnalyzeScriptForAssets, isAnalyzingAssets, onAddAsset, onRemoveAsset, onUpdateAssetImage, onLoadProject, onArchiveProject
}) => {
    const [script, setScript] = useState('');
    const [createKeyframes, setCreateKeyframes] = useState(true);
    const scriptFileInputRef = useRef<HTMLInputElement>(null);
    const projectFileInputRef = useRef<HTMLInputElement>(null);
    const archiveFileInputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        console.log("Submit button clicked. Script trimmed length:", script.trim().length);
        if (script.trim() && !isGenerating) {
            console.log("Calling onGenerate...");
            onGenerate(script, createKeyframes);
        } else {
            console.warn("Submit blocked: script empty or already generating.", { empty: !script.trim(), isGenerating });
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, callback: (s: string) => void) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            if (event.target?.result) callback(event.target.result as string);
        };
        reader.readAsText(file);
        e.target.value = '';
    };

    return (
        <div className="w-full max-w-6xl mx-auto flex flex-col gap-20 py-10">
            {/* 01: Visual Identity & World Building */}
            <section className="animate-in fade-in slide-in-from-bottom-6 duration-1000">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-6 px-4">
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-3">
                            <span className="w-6 h-6 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-black text-[10px] border border-indigo-500/30">01</span>
                            <h2 className="text-[10px] font-black text-white/40 uppercase tracking-[0.4em]">Cinematic Archetypes</h2>
                        </div>
                        <h3 className="text-3xl font-black text-white italic tracking-tighter">WORLD BUILDING</h3>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={() => projectFileInputRef.current?.click()}
                            className="px-6 py-3 bg-white/5 border border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest text-white/60 hover:text-white hover:bg-white/10 transition-all flex items-center gap-3 shadow-xl"
                        >
                            <RectangleStackIcon className="w-4 h-4 opacity-50" /> Local Ingest
                        </button>
                        <button
                            onClick={() => archiveFileInputRef.current?.click()}
                            className="px-6 py-3 bg-indigo-600/10 border border-indigo-500/30 rounded-2xl text-[10px] font-black uppercase tracking-widest text-indigo-400 hover:bg-indigo-600 hover:text-white transition-all flex items-center gap-3 shadow-xl"
                            title="Directly upload to the Vault (Supabase) for long-term archival."
                        >
                            <UploadCloudIcon className="w-4 h-4" /> Vault Sync
                        </button>
                    </div>
                    <input type="file" ref={projectFileInputRef} onChange={(e) => handleFileChange(e, onLoadProject)} accept=".json" className="hidden" />
                    <input type="file" ref={archiveFileInputRef} onChange={(e) => handleFileChange(e, onArchiveProject)} accept=".json" className="hidden" />
                </div>
                <AssetLibrary
                    assets={assets} onAddAsset={onAddAsset} onRemoveAsset={onRemoveAsset} onUpdateAssetImage={onUpdateAssetImage}
                    onAnalyzeScript={() => onAnalyzeScriptForAssets(script)} isAnalyzing={isAnalyzingAssets} hasScript={!!script.trim()}
                />
            </section>

            {/* 02: Narrative Breakdown */}
            <section className="animate-in fade-in slide-in-from-bottom-10 duration-1000 delay-300">
                <div className="flex flex-col gap-2 mb-8 px-4">
                    <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-lg bg-pink-500/20 text-pink-400 flex items-center justify-center font-black text-[10px] border border-pink-500/30">02</span>
                        <h2 className="text-[10px] font-black text-white/40 uppercase tracking-[0.4em]">Creative Intent</h2>
                    </div>
                    <h3 className="text-3xl font-black text-white italic tracking-tighter uppercase">Script Manifest</h3>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-[2.5rem] p-10 backdrop-blur-3xl shadow-2xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-[100px] -mr-32 -mt-32"></div>

                    <div className="flex justify-between items-center mb-8 relative z-10">
                        <p className="text-[11px] text-white/40 font-bold uppercase tracking-widest leading-none">Draft your scene beats or upload a screenplay</p>
                        <div className="flex gap-2">
                            <button type="button" onClick={() => scriptFileInputRef.current?.click()} className="p-3 bg-black/40 border border-white/5 rounded-xl hover:bg-white/10 text-white/40 hover:text-white transition-all"><FileUploadIcon className="w-4 h-4" /></button>
                            <button type="button" className="p-3 bg-black/40 border border-white/5 rounded-xl hover:bg-white/10 text-white/40 hover:text-white transition-all"><FileAudioIcon className="w-4 h-4" /></button>
                        </div>
                    </div>

                    <textarea
                        value={script} onChange={(e) => setScript(e.target.value)}
                        placeholder="EXT. STUDIO - TWILIGHT. The neon hums as the director enters... "
                        className="w-full h-64 bg-black/40 border border-white/10 rounded-[2rem] p-8 text-white focus:outline-none focus:border-indigo-500/50 transition-all font-serif italic text-xl leading-relaxed shadow-inner placeholder:text-white/10 relative z-10 scrollbar-hide"
                    />

                    <div className="mt-10 flex flex-col md:flex-row justify-between items-center gap-6 relative z-10">
                        <label className="flex items-center gap-4 cursor-pointer group">
                            <input type="checkbox" checked={createKeyframes} onChange={(e) => setCreateKeyframes(e.target.checked)} className="hidden" />
                            <div className={`w-12 h-6 rounded-full transition-all border p-1 flex items-center ${createKeyframes ? 'bg-indigo-600 border-indigo-400' : 'bg-black/60 border-white/10'}`}>
                                <div className={`w-4 h-4 bg-white rounded-full transition-all duration-300 shadow-md ${createKeyframes ? 'translate-x-6' : 'translate-x-0'}`}></div>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-black uppercase text-white tracking-[0.1em] group-hover:text-indigo-400 transition-colors">Visual Pre-Viz</span>
                                <span className="text-[9px] font-bold text-white/20 uppercase tracking-widest">Auto-Generate Stills</span>
                            </div>
                        </label>

                        <button
                            onClick={handleSubmit}
                            disabled={!script.trim() || isGenerating}
                            className="w-full md:w-auto px-12 py-5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/5 disabled:text-white/10 text-white font-black rounded-2xl uppercase italic tracking-tighter text-base transition-all shadow-[0_15px_40px_rgba(79,70,229,0.3)] hover:shadow-[0_20px_50px_rgba(79,70,229,0.5)] flex items-center justify-center gap-4 group/btn"
                        >
                            Initiate Breakdown
                            <ArrowRightIcon className="w-5 h-5 group-hover/btn:translate-x-1 transition-transform" />
                        </button>
                    </div>
                </div>
            </section>

            <input type="file" ref={scriptFileInputRef} className="hidden" onChange={(e) => handleFileChange(e, setScript)} accept=".txt,.pdf,.fdx" />
        </div>
    );
};

export default VeoProjectForm;
