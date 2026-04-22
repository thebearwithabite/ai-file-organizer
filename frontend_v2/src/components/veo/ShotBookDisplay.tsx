/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState } from 'react';
import type {
    LogEntry,
    ProjectAsset,
    Shot,
    ShotBook,
} from '../../types/veo';
import ActivityLog from './ActivityLog';
import ShotCard from './ShotCard';
import {
    SaveIcon,
    UploadCloudIcon,
    XMarkIcon,
    KeyIcon,
} from './icons';

interface ShotBookDisplayProps {
    shotBook: ShotBook;
    logEntries: LogEntry[];
    projectName: string | null;
    onNewProject: () => void;
    onUpdateShot: (shot: Shot) => void;
    onGenerateSpecificKeyframe: (shotId: string) => void;
    onRefineShot: (shotId: string, feedback: string) => void;
    allAssets: ProjectAsset[];
    onToggleAssetForShot: (shotId: string, assetId: string) => void;
    onSaveProject: () => void;
    onExportPackage: () => void;
    isProcessing: boolean;
    onStopGeneration: () => void;
    onApproveShot: (shotId: string, approved: boolean) => void;
    isServiceAccountActive: boolean;
    onCloudSync: () => void;
    onPushToResolve: () => void;
    ownerEmail: string;
}

const ShotBookDisplay: React.FC<ShotBookDisplayProps> = ({
    shotBook, logEntries, projectName, onNewProject, onUpdateShot, onGenerateSpecificKeyframe, onRefineShot, allAssets, onToggleAssetForShot,
    onSaveProject: _, onExportPackage: __, isProcessing: ___, onStopGeneration: ____, onGenerateVideo, onExtendVeoVideo, onUploadAdHocAsset, onRemoveAdHocAsset, onApproveShot,
    isServiceAccountActive, onCloudSync, onPushToResolve, ownerEmail: ______,
}) => {
    const [showSettings, setShowSettings] = useState(false);

    const groupedShots = shotBook.reduce((acc, shot) => {
        const sceneId = shot.id.substring(0, shot.id.lastIndexOf('_')) || 'SEQUENCE_OVERVIEW';
        if (!acc[sceneId]) acc[sceneId] = [];
        acc[sceneId].push(shot);
        return acc;
    }, {} as Record<string, Shot[]>);

    return (
        <div className="w-full flex flex-col gap-10 animate-in fade-in duration-1000">
            <header className="bg-black/40 backdrop-blur-3xl border border-white/10 rounded-[2.5rem] p-8 flex flex-col xl:flex-row justify-between items-center gap-8 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-[100px] -ml-32 -mt-32"></div>

                <div className="flex items-center gap-6 relative z-10 w-full xl:w-auto">
                    <div className={`w-16 h-16 rounded-[1.25rem] flex items-center justify-center shadow-2xl border transition-all duration-500 ${isServiceAccountActive ? 'bg-indigo-600 border-indigo-400 rotate-0' : 'bg-white/5 border-white/10 rotate-12'}`}>
                        {isServiceAccountActive ? (
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        ) : (
                            <UploadCloudIcon className="w-7 h-7 text-white opacity-20" />
                        )}
                    </div>
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-3">
                            <h2 className="text-3xl font-black text-white italic tracking-tighter uppercase leading-none">{projectName || 'UNNAMED_MISSION'}</h2>
                        </div>
                        <p className="text-[10px] text-white/30 font-black uppercase tracking-[0.4em] italic mb-1">
                            ACTIVE_SESSION // {projectName ? `vault/${projectName}.json` : 'temporary_cache'}
                        </p>
                        {isServiceAccountActive && (
                            <p className="text-[9px] text-indigo-400 font-black uppercase tracking-[0.2em] italic">
                                SECURE_PROTOCOL // SERVICE_ACCOUNT_ACTIVE
                            </p>
                        )}
                    </div>
                </div>

                <div className="flex flex-wrap gap-4 relative z-10 w-full xl:w-auto justify-end">
                    <div className="relative">
                        <div className={`p-4 rounded-2xl border flex items-center gap-3 ${isServiceAccountActive ? 'bg-indigo-900/20 border-indigo-500/50 text-indigo-400' : 'bg-red-900/10 border-red-500/30 text-red-400'}`}>
                            <KeyIcon className="w-5 h-5" />
                            <span className="text-[10px] font-black uppercase tracking-widest hidden sm:inline">
                                {isServiceAccountActive ? 'AUTH_SECURE' : 'AUTH_OFFLINE'}
                            </span>
                        </div>
                    </div>

                    <button
                        onClick={onCloudSync}
                        className="px-8 py-4 bg-white/5 hover:bg-white/10 text-white/60 text-[10px] font-black uppercase italic tracking-widest rounded-2xl border border-white/5 transition-all flex items-center gap-3"
                    >
                        <SaveIcon className="w-4 h-4" />
                        Sync to Vault
                    </button>

                    <button
                        onClick={onPushToResolve}
                        className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-black uppercase italic tracking-widest rounded-2xl transition-all shadow-[0_15px_40px_rgba(79,70,229,0.3)] flex items-center gap-3"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 2L2 7l10 5 10-5-10-5z" />
                            <path d="M2 17l10 5 10-5" />
                            <path d="M2 12l10 5 10-5" />
                        </svg>
                        Project to Resolve
                    </button>

                    <button
                        onClick={onNewProject}
                        className="px-8 py-4 bg-white/5 hover:bg-white/10 text-white/40 hover:text-white text-[10px] font-black uppercase tracking-widest rounded-2xl border border-white/5 transition-all"
                    >
                        Abort Unit
                    </button>
                </div>
            </header>

            <div className="flex flex-col 2xl:flex-row gap-10 items-start">
                <div className="w-full 2xl:flex-grow flex flex-col gap-12">
                    {(Object.entries(groupedShots) as [string, Shot[]][]).map(([sceneId, shots]) => (
                        <div key={sceneId} className="animate-in fade-in slide-in-from-bottom-6 duration-1000">
                            <div className="flex items-center gap-4 mb-8 px-4">
                                <div className="h-px flex-grow bg-white/5"></div>
                                <h3 className="text-[10px] font-black text-white/30 uppercase tracking-[0.5em] italic whitespace-nowrap">
                                    {sceneId.replace(/_/g, ' ')} // {shots.length} PRODUCTION UNITS
                                </h3>
                                <div className="h-px flex-grow bg-white/5"></div>
                            </div>
                            <div className="flex flex-col gap-10">
                                {shots.map((shot) => (
                                    <ShotCard
                                        key={shot.id}
                                        shot={shot}
                                        onUpdateShot={onUpdateShot}
                                        onGenerateSpecificKeyframe={onGenerateSpecificKeyframe}
                                        onRefineShot={onRefineShot}
                                        allAssets={allAssets}
                                        onToggleAssetForShot={onToggleAssetForShot}
                                        onGenerateVideo={onGenerateVideo}
                                        onExtendVeoVideo={onExtendVeoVideo}
                                        onUploadAdHocAsset={onUploadAdHocAsset}
                                        onRemoveAdHocAsset={onRemoveAdHocAsset}
                                        onApproveShot={onApproveShot}
                                    />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                <aside className="w-full 2xl:w-[450px] sticky top-10 self-start">
                    <ActivityLog entries={logEntries} />

                    <div className="mt-8 p-8 bg-indigo-600/5 border border-indigo-500/10 rounded-[2.5rem] backdrop-blur-3xl animate-in fade-in zoom-in-95 duration-1000 delay-500 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 blur-[50px] -mr-16 -mt-16"></div>
                        <h4 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.3em] mb-4 flex items-center gap-2 italic">
                            <InfoIcon className="w-3.5 h-3.5" /> Session Protocol
                        </h4>
                        <p className="text-[11px] text-white/40 leading-relaxed font-medium italic">
                            All artifacts generated during this session are being indexed into the Global Similarity Engine.
                            Reference clips from the Vault will be prioritized for rendering continuity.
                        </p>
                    </div>
                </aside>
            </div>
        </div>
    );
};

export default ShotBookDisplay;

const InfoIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></svg>
);
