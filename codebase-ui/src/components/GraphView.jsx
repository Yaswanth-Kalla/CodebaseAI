import ForceGraph2D from "react-force-graph-2d";
import { useEffect, useState, useRef } from "react";

export default function GraphView() {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const graphRef = useRef();

  useEffect(() => {
    setLoading(true);
    fetch("https://codebaseai-orv6.onrender.com/graph")
      .then(res => res.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
  }, []);

  if (loading) return (
    <div className="flex-1 h-full flex flex-col items-center justify-center bg-[#070B14] gap-3">
      <div className="flex gap-1.5">
        {[0, 1, 2].map(n => (
          <span key={n} className="w-2.5 h-2.5 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: `${n * 0.15}s` }} />
        ))}
      </div>
      <p className="text-gray-500 text-sm">Loading dependency graph...</p>
    </div>
  );

  if (error) return (
    <div className="flex-1 h-full flex flex-col items-center justify-center bg-[#070B14] gap-3">
      <span className="text-4xl">🕸️</span>
      <p className="text-gray-500 text-sm">Could not load graph — is the backend running?</p>
    </div>
  );

  if (!data.nodes?.length) return (
    <div className="flex-1 h-full flex flex-col items-center justify-center bg-[#070B14] gap-3">
      <span className="text-4xl">🕸️</span>
      <p className="text-gray-500 text-sm">No graph data yet — upload a codebase first</p>
    </div>
  );

  return (
    <div className="flex h-full bg-[#070B14] relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 h-10 border-b border-white/5 flex items-center px-5 z-10 bg-[#070B14]/80 backdrop-blur-sm">
        <span className="text-white text-sm font-medium">Dependency Graph</span>
        <span className="ml-3 text-gray-600 text-xs">{data.nodes.length} nodes · {data.links.length} links</span>
        {selectedNode && (
          <div className="ml-auto flex items-center gap-2 bg-white/5 border border-white/8 rounded-lg px-3 py-1">
            <span className="text-gray-400 text-xs">Selected:</span>
            <span className="text-violet-300 text-xs font-mono">{selectedNode.id}</span>
          </div>
        )}
      </div>

      <div className="flex-1 pt-10">
        <ForceGraph2D
          ref={graphRef}
          graphData={data}
          nodeAutoColorBy="group"
          backgroundColor="#070B14"
          nodeRelSize={5}
          linkColor={() => "rgba(139,92,246,0.2)"}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const label = String(node.id || "").split("/").pop();
            const fontSize = Math.max(10 / globalScale, 3);
            const r = 5;

            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
            ctx.fillStyle = node.color || "#7c3aed";
            ctx.shadowBlur = 8;
            ctx.shadowColor = node.color || "#7c3aed";
            ctx.fill();
            ctx.shadowBlur = 0;

            if (globalScale > 0.8) {
              ctx.font = `${fontSize}px monospace`;
              ctx.textAlign = "center";
              ctx.fillStyle = "rgba(209,213,219,0.85)";
              ctx.fillText(label, node.x, node.y + r + fontSize + 1);
            }
          }}
          onNodeClick={(node) => setSelectedNode(node)}
          onBackgroundClick={() => setSelectedNode(null)}
        />
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-5 bg-[#0D1220]/90 border border-white/8 rounded-xl px-4 py-3 text-xs text-gray-500">
        <p className="mb-1.5 text-gray-400 font-medium">Legend</p>
        <div className="space-y-1">
          <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-violet-500" />Module</div>
          <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-400" />Dependency</div>
        </div>
      </div>
    </div>
  );
}
