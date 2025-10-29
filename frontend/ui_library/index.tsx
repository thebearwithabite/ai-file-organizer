/**
 * Phase 3c · UI Library Index Layout
 * -----------------------------------
 * Root dashboard structure with Tailwind + ShadCN UI integration.
 */

import React, { useEffect, useState } from "react";
import ContinuityGraph from "./components/ContinuityGraph";

export default function UILibrary() {
  const [clips, setClips] = useState<any[]>([]);
  const [continuity, setContinuity] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      const res = await fetch("/api/clips");
      const data = await res.json();
      setClips(data);
      try {
        const man = await fetch("/api/manifest/default");
        const m = await man.json();
        setContinuity(m.continuity || []);
      } catch { setContinuity([]); }
      setLoading(false);
    }
    fetchData();
  }, []);

  if (loading) return <div className="p-6 text-gray-400">Loading library...</div>;

  return (
    <div className="p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">🎬 VEO Prompt Library</h1>
        <button className="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700">
          + Upload Clip
        </button>
      </header>

      <section className="grid grid-cols-4 gap-4">
        {clips.map((c) => (
          <div key={c.id} className="p-3 bg-gray-800 rounded-lg shadow hover:bg-gray-700">
            <div className="text-sm text-gray-400">{c.shot_id}</div>
            <div className="text-xs text-gray-500">{c.mood || "—"}</div>
            <div className="text-xs text-gray-500">{c.lighting_type || "—"}</div>
            <div className="text-xs text-blue-400">conf {c.confidence_score.toFixed(2)}</div>
          </div>
        ))}
      </section>

      <section className="bg-gray-800 p-4 rounded-lg">
        <h2 className="text-lg font-semibold text-white mb-2">Continuity Map</h2>
        <ContinuityGraph clips={clips} continuity={continuity}/>
      </section>
    </div>
  );
}
