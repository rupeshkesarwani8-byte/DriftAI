// Turns the /analyses/{id}/functions response into nodes and edges for the impact graph.
// Pure functions only (no React), so the logic is easy to test.

const RANK = { high: 3, medium: 2, low: 1 };
export const COL_X = { change: 0, file: 380, fn: 780 };
export const ROW = 96;

const better = (a, b) => ((RANK[b] || 0) > (RANK[a] || 0) ? b : a);

/**
 * changes: array of { entity, property, old_value, new_value, matches[], weak_matches[] }
 * Columns:  requirement change  ->  file  ->  function / constant
 */
export function buildGraph(changes, includeWeak = false) {
  const changeNodes = [];
  const fileMap = new Map(); // path -> node
  const fnMap = new Map(); // "path::qualname" -> node
  const edgeMap = new Map(); // "source>target" -> edge

  const addEdge = (source, target, confidence) => {
    const key = `${source}>${target}`;
    const old = edgeMap.get(key);
    if (old) {
      old.data.confidence = better(old.data.confidence, confidence);
    } else {
      edgeMap.set(key, { id: key, source, target, data: { confidence } });
    }
  };

  (changes || []).forEach((ch, i) => {
    const id = `c${i}`;
    const list = [...(ch.matches || []), ...(includeWeak ? ch.weak_matches || [] : [])];
    changeNodes.push({
      id,
      type: "change",
      data: {
        title: `${ch.entity} · ${ch.property}`,
        sub: `${ch.old_value} → ${ch.new_value}`,
        matched: list.length,
      },
    });
    list.forEach((m) => {
      const fileId = `f:${m.path}`;
      const fnId = `fn:${m.path}::${m.qualname}`;
      if (!fileMap.has(fileId)) fileMap.set(fileId, { id: fileId, type: "file", data: { path: m.path, count: 0 } });
      if (!fnMap.has(fnId)) {
        fnMap.set(fnId, {
          id: fnId,
          type: "fn",
          data: {
            name: m.qualname, kind: m.kind, path: m.path, start: m.start_line, end: m.end_line,
            confidence: m.confidence, score: m.score,
          },
        });
        fileMap.get(fileId).data.count += 1;
      } else {
        const d = fnMap.get(fnId).data;
        d.confidence = better(d.confidence, m.confidence);
        d.score = Math.max(d.score, m.score);
      }
      addEdge(id, fileId, m.confidence);
      addEdge(fileId, fnId, m.confidence);
    });
  });

  const files = [...fileMap.values()];
  // functions are listed grouped by file, in the same order as the files
  const fns = [];
  files.forEach((f) => fnMap.forEach((n) => { if (`f:${n.data.path}` === f.id) fns.push(n); }));

  const place = (list, x, tallest) => list.map((n, i) => ({
    ...n,
    position: { x, y: i * ROW + ((tallest - list.length) * ROW) / 2 },
  }));
  const tallest = Math.max(changeNodes.length, files.length, fns.length, 1);

  const nodes = [
    ...place(changeNodes, COL_X.change, tallest),
    ...place(files, COL_X.file, tallest),
    ...place(fns, COL_X.fn, tallest),
  ];
  const edges = [...edgeMap.values()];
  return {
    nodes,
    edges,
    rows: tallest,
    stats: { changes: changeNodes.length, files: files.length, functions: fns.length },
  };
}

/** All nodes and edges on a path through `nodeId` (everything upstream and downstream of it). */
export function connectedTo(nodeId, edges) {
  const out = new Map();
  const inn = new Map();
  edges.forEach((e) => {
    if (!out.has(e.source)) out.set(e.source, []);
    if (!inn.has(e.target)) inn.set(e.target, []);
    out.get(e.source).push(e.target);
    inn.get(e.target).push(e.source);
  });
  const nodes = new Set([nodeId]);
  const walk = (start, next) => {
    const stack = [start];
    while (stack.length) {
      const cur = stack.pop();
      (next.get(cur) || []).forEach((n) => {
        if (!nodes.has(n)) {
          nodes.add(n);
          stack.push(n);
        }
      });
    }
  };
  walk(nodeId, out);
  walk(nodeId, inn);
  const edgeIds = new Set(edges.filter((e) => nodes.has(e.source) && nodes.has(e.target)).map((e) => e.id));
  return { nodes, edgeIds };
}