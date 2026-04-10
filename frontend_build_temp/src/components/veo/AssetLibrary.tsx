/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState } from 'react';
import type { AssetType, ProjectAsset } from '../../types/veo';
import {
    CheckCircle2Icon,
    PlusIcon,
    SparklesIcon,
    UploadCloudIcon,
    XMarkIcon,
    ClipboardDocumentIcon,
} from './icons';

interface AssetLibraryProps {
    assets: ProjectAsset[];
    onAddAsset: (asset: ProjectAsset) => void;
    onRemoveAsset: (id: string) => void;
    onUpdateAssetImage: (id: string, file: File) => void;
    onAnalyzeScript: () => void;
    isAnalyzing: boolean;
    hasScript: boolean;
}

const AssetLibrary: React.FC<AssetLibraryProps> = ({
    assets,
    onAddAsset,
    onRemoveAsset,
    onUpdateAssetImage,
    onAnalyzeScript,
    isAnalyzing,
    hasScript,
}) => {
    const [allCopied, setAllCopied] = useState(false);
    const [addingAssetType, setAddingAssetType] = useState<AssetType | null>(null);
    const [newAssetName, setNewAssetName] = useState('');

    const handleImageUpload = async (
        id: string,
        event: React.ChangeEvent<HTMLInputElement>,
    ) => {
        const file = event.target.files?.[0];
        if (!file) return;
        onUpdateAssetImage(id, file);
    };

    const startAdding = (type: AssetType) => {
        setAddingAssetType(type);
        setNewAssetName('');
    };

    const cancelAdding = () => {
        setAddingAssetType(null);
        setNewAssetName('');
    };

    const confirmAdding = () => {
        if (newAssetName.trim() && addingAssetType) {
            onAddAsset({
                id: `manual-${Date.now()}`,
                name: newAssetName.trim(),
                description: 'Manually added asset',
                type: addingAssetType,
                image: null,
            });
            cancelAdding();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            confirmAdding();
        }
        if (e.key === 'Escape') {
            cancelAdding();
        }
    };

    const handleCopyAllAssets = () => {
        if (assets.length === 0) return;

        const text = assets.map(a =>
            `[${a.type.toUpperCase()}]\nName: ${a.name}\nDescription: ${a.description}`
        ).join('\n\n');

        navigator.clipboard.writeText(text);
        setAllCopied(true);
        setTimeout(() => setAllCopied(false), 2000);
    };

    const sections: { type: AssetType, label: string }[] = [
        { type: 'character', label: 'Characters' },
        { type: 'location', label: 'Locations' },
        { type: 'prop', label: 'Props' },
        { type: 'style', label: 'Styles' },
    ];

    return (
        <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-6">
                <div>
                    <h3 className="text-xl font-black text-white flex items-center gap-3 italic tracking-tighter">
                        <SparklesIcon className="w-6 h-6 text-indigo-400" />
                        ASSET LIBRARY
                    </h3>
                    <p className="text-xs text-white/40 mt-1 uppercase font-bold tracking-widest">
                        Visual Identity Archetypes & Continuity Hooks
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        type="button"
                        onClick={handleCopyAllAssets}
                        disabled={assets.length === 0}
                        className="px-5 py-2.5 bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all border border-white/5 flex items-center gap-2">
                        {allCopied ? <CheckCircle2Icon className="w-4 h-4 text-green-400" /> : <ClipboardDocumentIcon className="w-4 h-4" />}
                        Copy Metadata
                    </button>
                    <button
                        type="button"
                        onClick={onAnalyzeScript}
                        disabled={isAnalyzing || !hasScript}
                        className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/5 disabled:text-white/20 disabled:cursor-not-allowed text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all shadow-[0_5px_20px_rgba(79,70,229,0.3)] flex items-center gap-2">
                        {isAnalyzing ? (
                            <>
                                <div className="w-4 h-4 border-2 border-t-transparent border-white rounded-full animate-spin"></div>
                                Analyzing...
                            </>
                        ) : (
                            <>
                                <SparklesIcon className="w-4 h-4" />
                                Auto-Detect Agents
                            </>
                        )}
                    </button>
                </div>
            </div>

            <div className="space-y-12">
                {sections.map((section) => {
                    const sectionAssets = assets.filter((a) => a.type === section.type);
                    const isAddingThisType = addingAssetType === section.type;

                    return (
                        <div key={section.type} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                            <div className="flex justify-between items-center mb-5">
                                <div className="flex items-center gap-3">
                                    <div className="w-1 h-4 bg-indigo-500 rounded-full"></div>
                                    <h4 className="text-[10px] font-black text-white/60 uppercase tracking-[0.3em]">
                                        {section.label}
                                    </h4>
                                </div>
                                <button
                                    onClick={() => startAdding(section.type)}
                                    type="button"
                                    className="text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest flex items-center gap-1 transition-colors">
                                    <PlusIcon className="w-3 h-3" /> Add {section.label.slice(0, -1)}
                                </button>
                            </div>

                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                                {isAddingThisType && (
                                    <div className="bg-white/5 rounded-2xl border border-indigo-500/30 p-4 flex flex-col justify-center gap-3 animate-in fade-in zoom-in-95 duration-200 backdrop-blur-md">
                                        <p className="text-[10px] font-black text-white/40 uppercase tracking-widest leading-none">New {section.label.slice(0, -1)}:</p>
                                        <input
                                            autoFocus
                                            type="text"
                                            className="bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 w-full font-medium"
                                            placeholder="Name..."
                                            value={newAssetName}
                                            onChange={(e) => setNewAssetName(e.target.value)}
                                            onKeyDown={handleKeyDown}
                                        />
                                        <div className="flex gap-2 justify-end">
                                            <button
                                                onClick={cancelAdding}
                                                type="button"
                                                className="text-[10px] font-black px-3 py-1.5 text-white/40 hover:text-white rounded-lg transition-colors uppercase tracking-widest">
                                                Cancel
                                            </button>
                                            <button
                                                onClick={confirmAdding}
                                                type="button"
                                                className="text-[10px] font-black px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-all uppercase tracking-widest">
                                                Inject
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {sectionAssets.map((asset) => (
                                    <AssetCard
                                        key={asset.id}
                                        asset={asset}
                                        onRemove={() => onRemoveAsset(asset.id)}
                                        onUpload={(e) => handleImageUpload(asset.id, e)}
                                    />
                                ))}

                                {sectionAssets.length === 0 && !isAddingThisType && (
                                    <div className="col-span-full py-10 flex flex-col items-center justify-center border-2 border-dashed border-white/5 rounded-2xl text-white/20">
                                        <RectangleStackIcon className="w-6 h-6 mb-2 opacity-50" />
                                        <p className="text-[10px] uppercase font-black tracking-[0.2em]">No {section.label} Registry Found</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

interface AssetCardProps {
    asset: ProjectAsset;
    onRemove: () => void;
    onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const AssetCard = ({ asset, onRemove, onUpload }: AssetCardProps) => {
    const [copied, setCopied] = useState(false);

    const handleCopyDescription = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        const textToCopy = `Name: ${asset.name}\nDescription: ${asset.description}`;
        navigator.clipboard.writeText(textToCopy);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="group relative bg-white/5 rounded-2xl border border-white/10 overflow-hidden flex flex-col transition-all hover:border-white/20 hover:bg-white/10 shadow-xl">
            <button
                onClick={onRemove}
                type="button"
                className="absolute top-2 right-2 z-20 bg-black/60 backdrop-blur-md text-white/60 hover:text-white rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-all border border-white/10 scale-90 group-hover:scale-100">
                <XMarkIcon className="w-3 h-3" />
            </button>

            <div className="aspect-[4/3] bg-black/40 relative overflow-hidden">
                {asset.image ? (
                    <img
                        src={`data:${asset.image.mimeType};base64,${asset.image.base64}`}
                        alt={asset.name}
                        className="w-full h-full object-cover opacity-60 group-hover:opacity-100 group-hover:scale-105 transition-all duration-700"
                    />
                ) : (
                    <label className="absolute inset-0 flex flex-col items-center justify-center cursor-pointer hover:bg-white/5 transition-all group/upload">
                        <UploadCloudIcon className="w-8 h-8 text-white/10 mb-2 group-hover/upload:text-indigo-400 group-hover/upload:scale-110 transition-all duration-300" />
                        <span className="text-[9px] font-black uppercase text-white/20 tracking-widest group-hover/upload:text-indigo-400">Upload Still</span>
                        <input
                            type="file"
                            className="hidden"
                            onChange={onUpload}
                            accept="image/png, image/jpeg, image/webp"
                        />
                    </label>
                )}
                {asset.image && (
                    <label className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-md p-2 rounded-full cursor-pointer hover:bg-indigo-600 border border-white/10 opacity-0 group-hover:opacity-100 transition-all scale-75 group-hover:scale-100">
                        <UploadCloudIcon className="w-3 h-3 text-white" />
                        <input
                            type="file"
                            className="hidden"
                            onChange={onUpload}
                            accept="image/png, image/jpeg, image/webp"
                        />
                    </label>
                )}
                {asset.image && (
                    <div className="absolute top-2 left-2 bg-indigo-500 shadow-[0_0_15px_rgba(79,70,229,0.5)] rounded-full p-1 border border-white/20">
                        <CheckCircle2Icon className="w-3 h-3 text-white" />
                    </div>
                )}
            </div>

            <div className="p-4 flex-grow flex flex-col gap-2">
                <h5 className="text-[11px] font-black text-white italic tracking-tight truncate leading-tight uppercase">
                    {asset.name}
                </h5>
                <div className="flex items-start justify-between gap-3 flex-1">
                    <p className="text-[10px] text-white/40 line-clamp-2 leading-relaxed font-medium">
                        {asset.description}
                    </p>
                    <button
                        type="button"
                        onClick={handleCopyDescription}
                        className="text-white/20 hover:text-white transition-colors flex-shrink-0 mt-0.5"
                        title="Copy Name & Description">
                        {copied ? <CheckCircle2Icon className="w-3 h-3 text-green-400" /> : <ClipboardDocumentIcon className="w-3 h-3" />}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AssetLibrary;

const RectangleStackIcon: React.FC<React.SVGProps<SVGSVGElement>> = (
    props,
) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...props}
    >
        <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
        <path d="M7 7h10" />
        <path d="M7 12h10" />
        <path d="M7 17h10" />
    </svg>
);
