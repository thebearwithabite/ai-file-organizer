/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState } from 'react';
import {
    ShotStatus,
    VeoStatus,
} from '../../types/veo';
import type {
    ProjectAsset,
    Shot,
} from '../../types/veo';
import {
    FilmIcon,
    FastForwardIcon,
    LinkIcon,
} from './icons';

interface ShotCardProps {
    shot: Shot;
    onUpdateShot: (shot: Shot) => void;
    onGenerateSpecificKeyframe: (shotId: string) => void;
    onRefineShot: (shotId: string, feedback: string) => void;
    allAssets: ProjectAsset[];
    onToggleAssetForShot: (shotId: string, assetId: string) => void;
    onGenerateVideo: (shotId: string, useKeyframe: boolean) => void;
    onExtendVeoVideo: (originalShotId: string, prompt: string) => void;
    onUploadAdHocAsset: (shotId: string, file: File) => void;
    onRemoveAdHocAsset: (shotId: string, index: number) => void;
    onApproveShot: (shotId: string, approved: boolean) => void;
}

const ShotCard: React.FC<ShotCardProps> = ({
    shot, onUpdateShot, onGenerateSpecificKeyframe: _onGenerateSpecificKeyframe, onRefineShot: _onRefineShot, allAssets, onToggleAssetForShot: _onToggleAssetForShot, onGenerateVideo, onApproveShot,
}) => {
    const [copyButtonText, setCopyButtonText] = useState('Copy JSON');
    const [useKeyframeAsReference] = useState(shot.veoUseKeyframeAsReference ?? true);
    const [referenceUrl, setReferenceUrl] = useState(shot.veoReferenceUrl || '');

    const isExtensionSegment = shot.veoJson?.unit_type === 'extend';

    const renderImagePlaceholder = () => {
        if (isExtensionSegment && !shot.keyframePromptText && !shot.keyframeImage) {
            return <div className="flex flex-col items-center text-indigo-400 opacity-40"><FastForwardIcon className="w-12 h-12 mb-2" /><span className="text-[10px] font-black uppercase tracking-widest leading-none">Extension Segment</span></div>;
        }
        if (shot.status === ShotStatus.GENERATING_IMAGE || shot.status === ShotStatus.GENERATING_JSON) return <div className="flex flex-col items-center text-white/20"><FilmIcon className="w-12 h-12 mb-2 animate-pulse" /><span className="text-[10px] font-black uppercase tracking-widest leading-none">Processing Arc...</span></div>;
        return <div className="flex flex-col items-center text-white/10"><FilmIcon className="w-12 h-12 mb-2" /><span className="text-[10px] font-black uppercase tracking-widest leading-none">No Shot Preview</span></div>;
    };

    return (
        <div className={`rounded-[2.5rem] p-8 border transition-all duration-500 ${shot.isApproved ? 'bg-indigo-600/5 border-indigo-500/30 shadow-2xl overflow-hidden relative' : 'bg-white/5 border-white/10'}`}>
            {shot.isApproved && <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 blur-[50px] -mr-16 -mt-16"></div>}

            <div className="flex flex-col lg:flex-row items-start gap-10">
                <div className="w-full lg:w-1/3">
                    <div className="aspect-video bg-black/60 rounded-3xl overflow-hidden border border-white/5 mb-6 flex items-center justify-center relative group shadow-inner">
                        {shot.veoStatus === VeoStatus.COMPLETED && shot.veoVideoUrl ? (
                            <video src={shot.veoVideoUrl} controls className="w-full h-full object-cover" />
                        ) : shot.keyframeImage ? (
                            <img src={`data:image/png;base64,${shot.keyframeImage}`} className="w-full h-full object-cover" />
                        ) : renderImagePlaceholder()}

                        {(shot.veoStatus === VeoStatus.GENERATING || shot.veoStatus === VeoStatus.QUEUED) && (
                            <div className="absolute inset-0 bg-black/80 flex flex-col items-center justify-center backdrop-blur-sm">
                                <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                                <p className="text-white text-[10px] font-black uppercase tracking-[0.3em] animate-pulse italic">Rendering Narrative</p>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center justify-between mb-3 px-1">
                        <h3 className="text-2xl font-black text-white italic tracking-tighter uppercase">{shot.id}</h3>
                        {shot.isApproved && (
                            <span className="bg-indigo-500 text-white text-[9px] font-black px-3 py-1 rounded-full uppercase tracking-widest italic shadow-[0_0_15px_rgba(79,70,229,0.5)]">LOCKED</span>
                        )}
                    </div>

                    <p className="text-[9px] text-white/20 font-black uppercase tracking-[0.4em] mb-4 px-1">{shot.sceneName || 'UNNAMED SCENE'}</p>
                    <div className="p-5 rounded-2xl bg-black/40 border border-white/5 text-white/70 italic text-sm leading-relaxed mb-6 font-serif shadow-inner">
                        "{shot.pitch}"
                    </div>

                    <div className="flex flex-wrap gap-2 px-1">
                        {shot.selectedAssetIds?.map(id => {
                            const asset = allAssets.find(a => a.id === id);
                            if (!asset || !asset.image) return null;
                            return <img key={id} src={`data:${asset.image.mimeType};base64,${asset.image.base64}`} className="w-10 h-10 object-cover rounded-xl border border-white/10 hover:border-indigo-500/50 transition-all hover:scale-110" title={asset.name} />;
                        })}
                    </div>
                </div>

                <div className="w-full lg:w-2/3 flex flex-col h-full self-stretch">
                    <div className="flex-grow h-[300px] overflow-auto bg-black/60 rounded-3xl p-6 border border-white/5 font-mono text-[10px] relative group shadow-inner scrollbar-hide">
                        <pre className="text-indigo-400/80 leading-relaxed">
                            <code>{shot.veoJson ? JSON.stringify(shot.veoJson, null, 2) : '// Awaiting Director Breakdown...'}</code>
                        </pre>
                        <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-all translate-y-2 group-hover:translate-y-0">
                            <button
                                onClick={() => {
                                    navigator.clipboard.writeText(JSON.stringify(shot.veoJson, null, 2));
                                    setCopyButtonText('Copied!');
                                    setTimeout(() => setCopyButtonText('Copy JSON'), 2000);
                                }}
                                className="px-3 py-1.5 bg-white/10 backdrop-blur-md rounded-lg hover:bg-white/20 text-white text-[9px] font-black uppercase tracking-widest transition-all"
                            >
                                {copyButtonText}
                            </button>
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-4 mt-8 items-center justify-between px-2">
                        <div className="flex gap-4 items-center">
                            {!shot.isApproved ? (
                                <button
                                    onClick={() => onApproveShot(shot.id, true)}
                                    className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-black rounded-2xl text-[10px] uppercase tracking-widest italic transition-all shadow-[0_10px_30px_rgba(79,70,229,0.3)]"
                                >
                                    Lock Sequence
                                </button>
                            ) : (
                                <button
                                    onClick={() => onApproveShot(shot.id, false)}
                                    className="px-8 py-3.5 bg-white/5 text-white/40 hover:text-white rounded-2xl text-[10px] font-black uppercase tracking-widest border border-white/5 transition-all"
                                >
                                    Unlock
                                </button>
                            )}

                            <div className="h-6 w-px bg-white/10 mx-2"></div>

                            {shot.veoStatus !== VeoStatus.COMPLETED && (
                                <button
                                    onClick={() => onGenerateVideo(shot.id, useKeyframeAsReference)}
                                    disabled={!shot.isApproved}
                                    className={`px-8 py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest italic transition-all ${shot.isApproved ? 'bg-pink-600 hover:bg-pink-500 text-white shadow-[0_10px_30px_rgba(219,39,119,0.3)]' : 'bg-white/5 text-white/5 cursor-not-allowed'}`}
                                >
                                    Generate Video
                                </button>
                            )}
                        </div>

                        {shot.veoStatus !== VeoStatus.COMPLETED && (
                            <div className="flex-grow max-w-md relative group/link">
                                <LinkIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20 group-focus-within/link:text-indigo-400 transition-colors" />
                                <input
                                    type="text"
                                    value={referenceUrl}
                                    onChange={(e) => {
                                        setReferenceUrl(e.target.value);
                                        onUpdateShot({ ...shot, veoReferenceUrl: e.target.value });
                                    }}
                                    placeholder="Cloud Source Reference..."
                                    className="w-full bg-white/5 border border-white/5 rounded-2xl pl-11 pr-4 py-3.5 text-[10px] text-white/60 font-mono focus:border-indigo-500/50 focus:outline-none transition-all placeholder:text-white/5"
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ShotCard;
