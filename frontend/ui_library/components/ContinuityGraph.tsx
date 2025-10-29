/**
 * Phase 3c · ContinuityGraph Component
 * ------------------------------------
 * Renders a force-directed graph showing visual continuity between clips.
 */

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface Node { id: string; confidence: number; }
interface Link { source: string; target: string; score: number; }

interface Props {
  clips: Node[];
  continuity: Link[];
}

export default function ContinuityGraph({ clips, continuity }: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!clips.length || !continuity.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 700, height = 450;
    const simulation = d3.forceSimulation(clips as any)
      .force("link", d3.forceLink(continuity).id((d: any) => d.id).distance(150))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(continuity)
      .enter().append("line")
      .attr("stroke-width", d => 2 + d.score * 3);

    const node = svg.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(clips)
      .enter().append("circle")
      .attr("r", d => 8 + d.confidence * 8)
      .attr("fill", "#3b82f6")
      .call(d3.drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          (d as any).fx = d.x;
          (d as any).fy = d.y;
        })
        .on("drag", (event, d) => {
          (d as any).fx = event.x;
          (d as any).fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          (d as any).fx = null;
          (d as any).fy = null;
        }));

    node.append("title").text(d => d.id);

    simulation.on("tick", () => {
      link
        .attr("x1", d => (d.source as any).x)
        .attr("y1", d => (d.source as any).y)
        .attr("x2", d => (d.target as any).x)
        .attr("y2", d => (d.target as any).y);
      node
        .attr("cx", d => (d as any).x)
        .attr("cy", d => (d as any).y);
    });

  }, [clips, continuity]);

  return <svg ref={svgRef} width="100%" height="450" className="rounded-lg bg-gray-900"/>;
}
