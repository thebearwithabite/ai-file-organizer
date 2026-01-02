/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useEffect, useRef } from 'react';
import { LogType } from '../../types/veo';
import type { LogEntry } from '../../types/veo';
import {
    CheckCircle2Icon,
    InfoIcon,
    MessageSquareTextIcon,
    XCircleIcon,
} from './icons';

interface ActivityLogProps {
    entries: LogEntry[];
}

const LogIcon: React.FC<{ type: LogType }> = ({ type }) => {
    switch (type) {
        case LogType.SUCCESS:
            return <CheckCircle2Icon className="w-4 h-4 text-green-400" />;
        case LogType.ERROR:
            return <XCircleIcon className="w-4 h-4 text-red-400" />;
        case LogType.STEP:
            return <MessageSquareTextIcon className="w-4 h-4 text-indigo-400" />;
        case LogType.INFO:
        default:
            return <InfoIcon className="w-4 h-4 text-white/30" />;
    }
};

const ActivityLog: React.FC<ActivityLogProps> = ({ entries }) => {
    const logContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [entries]);

    return (
        <div className="w-full bg-black/40 backdrop-blur-md border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
                <h3 className="text-sm font-black text-white uppercase tracking-[0.2em] italic">
                    Director's Log
                </h3>
                <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-red-500/50 animate-pulse"></div>
                    <div className="w-2 h-2 rounded-full bg-gray-700"></div>
                    <div className="w-2 h-2 rounded-full bg-gray-700"></div>
                </div>
            </div>
            <div
                ref={logContainerRef}
                className="h-64 overflow-y-auto p-4 space-y-3 font-mono text-[11px] scrollbar-hide">
                {entries.map((entry, index) => (
                    <div key={index} className="flex items-start gap-4 animate-in fade-in slide-in-from-left-2 duration-300">
                        <span className="text-white/20 whitespace-nowrap">{entry.timestamp}</span>
                        <div className="flex-shrink-0 mt-0.5 opacity-80">
                            <LogIcon type={entry.type} />
                        </div>
                        <p className="flex-1 text-white/70 break-words leading-relaxed font-medium">{entry.message}</p>
                    </div>
                ))}
                {entries.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full gap-2 opacity-20">
                        <div className="w-8 h-px bg-white/50"></div>
                        <p className="text-[10px] uppercase font-black tracking-widest">
                            Awaiting Sequence Start
                        </p>
                        <div className="w-8 h-px bg-white/50"></div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ActivityLog;
