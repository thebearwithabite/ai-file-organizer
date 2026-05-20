import React from 'react';
import { createRoot } from 'react-dom/client';
import ShotCard from './ShotCard';
import '../../index.css';
import { Shot } from '../../types';

// Mock functions
const mockOnApprove = (id: string, approved: boolean) => console.log('Approve', id, approved);
const mockOnGenerate = (id: string, useKeyframe: boolean) => console.log('Generate', id, useKeyframe);
const mockOnUpdate = (shot: Shot) => console.log('Update', shot);

// Mock data
const mockShot: Shot = {
    id: 'shot-1',
    pitch: 'A sweeping drone shot of a futuristic city.',
    selectedAssetIds: [],
    veoStatus: 'completed',
    veoJson: {
        "prompt": "A sweeping drone shot of a futuristic city.",
        "camera": "drone",
        "lighting": "cinematic"
    },
    isApproved: false,
    startTime: 0,
    endTime: 5,
    createdAt: new Date().toISOString()
};

const root = createRoot(document.getElementById('root')!);
root.render(
    <div className="p-8 bg-neutral-900 min-h-screen text-white">
        <ShotCard
            shot={mockShot}
            allAssets={[]}
            onApproveShot={mockOnApprove}
            onGenerateVideo={mockOnGenerate}
            onUpdateShot={mockOnUpdate}
        />
    </div>
);
