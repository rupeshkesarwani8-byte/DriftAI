import { useMemo, useState } from "react";
import { Background, Controls, Handle, Position, ReactFlow } from "@xyflow/react";
import { Braces, FileCode, GitCompare } from "lucide-react";
import "@xyflow/react/dist/style.css";
import { buildGraph, connectedTo, ROW } from "../graphModel";
import "../graph.css";

function ChangeNode({ data }) {
  return (
    <div className="ig-node ig-change">
      <div className="ig-tag"><GitCompare size={12} /> REQUIREMENT CHANGE</div>
      <div className="ig-title" title={data.title}>{data.title}</div>
      <div className="ig-sub">{data.sub}</div>
      {data.matched === 0 && <div className="ig-none">no match in code</div>}
      <Handle type="source" position={Position.Right} className="ig-handle" />
    </div>
  );
}

function FileNode({ data }) {
  const i = data.path.lastIndexOf("/");
  const dir = i >= 0 ? data.path.slice(0, i + 1) : "";
  const name = i >= 0 ? data.path.slice(i + 1) : data.path;
  return (
    <div className="ig-node ig-file">
      <Handle type="target" position={Position.Left} className="ig-handle" />
      <div className="ig-tag"><FileCode size={12} /> FILE</div>
      <div className="ig-title" title={data.path}>
        <span className="ig-dir">{dir}</span>{name}
      </div>
      <div className="ig-sub">{data.count} item{data.count === 1 ? "" : "s"} to check</div>
      <Handle type="source" position={Position.Right} className="ig-handle" />
    </div>
  );
}

function FnNode({ data }) {
  return (
    <div className={`ig-node ig-fn ig-c-${data.confidence}`} title={`${data.path}:${data.start}-${data.end}`}>
      <Handle type="target" position={Position.Left} className="ig-handle" />
      <div className="ig-tag">
        <Braces size={12} /> {data.kind.toUpperCase()}
        <span className={`ig-conf ig-conf-${data.confidence}`}>{data.confidence}</span>
      </div>
      <div className="ig-title">{data.name}</div>
      <div className="ig-sub">lines {data.start}-{data.end} · score {data.score}</div>
    </div>
  );
}

const nodeTypes = { change: ChangeNode, file: FileNode, fn: FnNode };

/** Requirement change -> file -> function graph. Click a node to highlight its path. */
export default function ImpactGraph({ changes }) {
  const [includeWeak, setIncludeWeak] = useState(false);
  const [picked, setPicked] = useState(null);

  const graph = useMemo(() => buildGraph(changes, includeWeak), [changes, includeWeak]);
  const focus = useMemo(() => (picked ? connectedTo(picked, graph.edges) : null), [picked, graph]);

  const nodes = useMemo(
    () => graph.nodes.map((n) => ({
      ...n,
      className: focus ? (focus.nodes.has(n.id) ? "ig-on" : "ig-dim") : "",
      draggable: false,
    })),
    [graph, focus]
  );
  const edges = useMemo(
    () => graph.edges.map((e) => ({
      ...e,
      type: "smoothstep",
      animated: e.data.confidence === "high",
      className: `ig-edge ig-e-${e.data.confidence} ${focus ? (focus.edgeIds.has(e.id) ? "ig-on" : "ig-dim") : ""}`,
    })),
    [graph, focus]
  );

  const height = Math.min(680, Math.max(340, graph.rows * ROW + 90));
  const drawn = graph.stats.functions;

  return (
    <div className="ig-wrap">
      <div className="ig-bar">
        <div className="ig-stats">
          {graph.stats.changes} change{graph.stats.changes === 1 ? "" : "s"} → {graph.stats.files} file
          {graph.stats.files === 1 ? "" : "s"} → {drawn} function{drawn === 1 ? "" : "s"}
        </div>
        <label className="ig-check">
          <input type="checkbox" checked={includeWeak} onChange={(e) => { setIncludeWeak(e.target.checked); setPicked(null); }} />
          Include weak matches
        </label>
        <div className="ig-legend">
          <span className="ig-dot ig-dot-high" /> high
          <span className="ig-dot ig-dot-medium" /> medium
          <span className="ig-dot ig-dot-low" /> low
        </div>
      </div>

      {drawn === 0 && (
        <div className="ig-hint">
          No strong match to draw. {includeWeak ? "" : "Tick “Include weak matches” to see the weaker guesses."}
        </div>
      )}

      <div className="ig-flow" style={{ height }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          colorMode="dark"
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.25}
          maxZoom={1.6}
          nodesDraggable={false}
          nodesConnectable={false}
          onNodeClick={(_, n) => setPicked((p) => (p === n.id ? null : n.id))}
          onPaneClick={() => setPicked(null)}
        >
          <Background gap={22} size={1} color="rgba(255,255,255,.07)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <p className="ig-note">Click a box to highlight everything connected to it. Scroll to zoom, drag the background to move.</p>
    </div>
  );
}