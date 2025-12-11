from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Tarkov Quest Tree</title>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --card: #0b1223;
      --stroke: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #3b82f6;
      --accent-2: #22d3ee;
    }
    body {
      margin: 0;
      background: radial-gradient(120% 120% at 20% 20%, #11182c, #0a0f1d);
      color: var(--text);
      font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
      overflow: hidden;
      display: grid;
      grid-template-columns: 2fr 1fr;
      height: 100vh;
    }
    #chart { position: relative; border-right: 1px solid #1f2937; }
    #panel {
      background: var(--panel);
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: -6px 0 24px rgba(0,0,0,0.4);
    }
    #panel h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0.2px;
    }
    #panel .meta {
      color: var(--muted);
      font-size: 13px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .chip { background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.4); color: #bfdbfe; padding: 2px 8px; border-radius: 999px; }
    .section {
      background: var(--card);
      border: 1px solid var(--stroke);
      border-radius: 10px;
      padding: 10px 12px;
    }
    .section h3 { margin: 0 0 6px; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; }
    .section ul { margin: 0; padding-left: 18px; color: #e5e7eb; font-size: 14px; line-height: 1.45; }
    .section p { margin: 0; color: #e5e7eb; }
    #legend { font-size: 12px; color: var(--muted); }
    #open-link { padding: 10px 12px; border: 1px solid var(--accent); background: rgba(59,130,246,0.15); color: #bfdbfe; border-radius: 8px; cursor: pointer; font-weight: 600; }
    #open-link:disabled { opacity: 0.4; cursor: not-allowed; border-color: var(--stroke); }
    svg { width: 100%; height: 100%; background: transparent; }
    .node { cursor: pointer; }
    .node circle { stroke: var(--stroke); stroke-width: 1.5; }
    .node text { pointer-events: none; font-size: 12px; fill: var(--text); text-shadow: 0 1px 2px rgba(0,0,0,0.6); }
    .link { stroke: rgba(148,163,184,0.5); stroke-width: 1.6px; }
    .node.selected circle { stroke: var(--accent-2); stroke-width: 3; }
    .node.ancestor circle { stroke: #38bdf8; stroke-width: 3; filter: drop-shadow(0 0 6px rgba(56,189,248,0.75)); }
    .link.ancestor-link { stroke: rgba(56,189,248,0.85); stroke-width: 2.4px; }
    #search { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--stroke); background: #0b1223; color: var(--text); }
    #search-results { display: flex; flex-wrap: wrap; gap: 6px; padding: 4px 0 8px; }
    #search-results .pill { padding: 6px 10px; border-radius: 999px; border: 1px solid var(--stroke); background: #0b1223; color: var(--text); cursor: pointer; font-size: 12px; }
    #search-results .pill:hover { border-color: var(--accent); color: #bfdbfe; }
  </style>
</head>
<body>
  <div id="chart"></div>
  <div id="panel">
    <input id="search" placeholder="Search quests..." />
    <div id="search-results"></div>
    <div id="legend">Click nodes to expand details. Scroll / drag to navigate.</div>
    <div id="card">
      <h1>Select a quest</h1>
      <div class="meta"></div>
      <button id="open-link" class="primary">Open wiki page</button>
      <div class="section" id="objectives-box"><h3>Objectives</h3><ul></ul></div>
      <div class="section" id="rewards-box"><h3>Rewards</h3><ul></ul></div>
      <div class="section" id="dialogue-box"><h3>Dialogue</h3><ul></ul></div>
      <div class="section" id="previous-box"><h3>Previous</h3><p>-</p></div>
      <div class="section" id="leads-box"><h3>Leads to</h3><p>-</p></div>
    </div>
  </div>

  <script>
    // Raw data
    const nodes = __NODES__;
    const links = __LINKS__.map(l => ({ source: l.source, target: l.target }));
    const nodesById = new Map(nodes.map(n => [n.id, n]));

    const margin = 100;
    const columnGap = 220;
    const height = window.innerHeight;
    const width = Math.max(window.innerWidth * 0.65, margin * 2 + columnGap * 8);

    // Initial positions based on level, random y to spread vertically
    nodes.forEach(n => {
      n.x = margin + (n.level || 0) * columnGap + (Math.random() - 0.5) * 20;
      n.y = margin + (Math.random() * (height - 2 * margin));
      if ((n.level || 0) === 0) {
        n.fx = margin; // lock x for roots
      }
    });

    const zoom = d3.zoom().scaleExtent([0.3, 3]).on("zoom", (event) => {
      g.attr("transform", event.transform);
    });
    const svg = d3.select("#chart")
      .append("svg")
      .attr("viewBox", [0, 0, width, height])
      .call(zoom);

    const g = svg.append("g");

    const link = g.append("g")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", 0.5)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("class", "link");

    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("class", "node")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    node.append("circle")
      .attr("r", 10)
      .attr("fill", d => colorByTrader(d.given_by));

    node.append("text")
      .attr("x", 12)
      .attr("y", 4)
      .text(d => d.name);

    node.on("click", (_, d) => {
      selectNode(d);
      highlightAncestry(d.id);
    });

    // Custom force to encourage targets to sit to the right of their sources
    function forceRightBias(strength = 0.1, gap = 80) {
      return (alpha) => {
        links.forEach(l => {
          const s = typeof l.source === "object" ? l.source : nodesById.get(l.source);
          const t = typeof l.target === "object" ? l.target : nodesById.get(l.target);
          if (!s || !t) return;
          const desired = s.x + gap;
          const delta = desired - t.x;
          t.vx += delta * strength * alpha;
        });
      };
    }

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(140).strength(0.7))
      .force("charge", d3.forceManyBody().strength(-150))
      .force("collide", d3.forceCollide(14))
      .force("x", d3.forceX(d => margin + (d.level || 0) * columnGap).strength(d => (d.level || 0) === 0 ? 1 : 0.6))
      .force("y", d3.forceY(height / 2).strength(0.02))
      .force("rightBias", forceRightBias(0.22, 90))
      .velocityDecay(0.42)
      .alpha(1)
      .on("tick", ticked);

    let coolTimer = null;
    function warmup() {
      simulation.alphaTarget(0.3).restart();
      if (coolTimer) clearTimeout(coolTimer);
      coolTimer = setTimeout(() => simulation.alphaTarget(0), 20000);
    }

    function ticked() {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    }

    function dragstarted(event) {
      if (!event.active) simulation.alphaTarget(0.2).restart();
      if ((event.subject.level || 0) === 0) {
        event.subject.fx = margin; // keep roots on the left
        event.subject.fy = event.subject.y; // allow y dragging
      } else {
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      warmup();
    }

    function dragged(event) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event) {
      if (!event.active) simulation.alphaTarget(0);
      if ((event.subject.level || 0) === 0) {
        event.subject.fx = margin; // keep roots pinned on the left, free y
        event.subject.fy = null;
      } else {
        event.subject.fx = null;
        event.subject.fy = null;
      }
    }

    function colorByTrader(trader) {
      const palette = {
        "Prapor": "#3b82f6",
        "Therapist": "#22d3ee",
        "Fence": "#a78bfa",
        "Skier": "#f59e0b",
        "Peacekeeper": "#34d399",
        "Mechanic": "#f87171",
        "Ragman": "#c084fc",
        "Jaeger": "#f97316",
        "Lightkeeper": "#eab308",
        "BTR Driver": "#06b6d4",
        "Ref": "#8b5cf6"
      };
      return palette[trader] || "#64748b";
    }

    const card = document.getElementById("card");
    function setList(boxId, items) {
      const ul = document.querySelector(`#${boxId} ul`);
      ul.innerHTML = "";
      if (!items || !items.length) {
        ul.innerHTML = "<li>-</li>";
        return;
      }
      items.forEach((t) => {
        const li = document.createElement("li");
        li.textContent = t;
        ul.appendChild(li);
      });
    }

    function focusNode(n) {
      selectNode(n);
      highlightAncestry(n.id);
      const tx = width / 2 - n.x;
      const ty = height / 2 - n.y;
      svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(1));
      warmup();
    }

    function setLinks(boxId, list) {
      const container = document.querySelector(`#${boxId} p`);
      container.innerHTML = "";
      if (!list || !list.length) {
        container.textContent = "-";
        return;
      }
      list.forEach((name, idx) => {
        const linkEl = document.createElement("a");
        linkEl.href = "#";
        linkEl.textContent = name;
        linkEl.style.color = "#38bdf8";
        linkEl.style.textDecoration = "none";
        linkEl.style.marginRight = "8px";
        linkEl.addEventListener("click", (e) => {
          e.preventDefault();
          const target = nodes.find(n => n.id === name);
          if (target) {
            focusNode(target);
          }
        });
        container.appendChild(linkEl);
        if (idx < list.length - 1) {
          const sep = document.createElement("span");
          sep.textContent = " ";
          container.appendChild(sep);
        }
      });
    }

    function selectNode(d) {
      node.classed("selected", n => n.id === d.id);
      card.querySelector("h1").textContent = d.name;
      card.querySelector(".meta").innerHTML = `
        <span class="chip">Given by: ${d.given_by || "-"}</span>
        <span class="chip">Location: ${d.location || "-"}</span>
      `;
      openLinkBtn.disabled = !d.url;
      openLinkBtn.onclick = () => {
        if (d.url) window.open(d.url, "_blank");
      };
      setList("objectives-box", d.objectives);
      setList("rewards-box", d.rewards);
      setList("dialogue-box", d.dialogue);
      setLinks("previous-box", d.previous);
      setLinks("leads-box", d.leads_to);
    }

    const search = document.getElementById("search");
    const searchResults = document.getElementById("search-results");
    const openLinkBtn = document.getElementById("open-link");

    // Build reverse adjacency for ancestor highlighting (normalize ids)
    function buildParents() {
      const pmap = new Map();
      links.forEach(l => {
        const src = l.source.id ? l.source.id : l.source;
        const tgt = l.target.id ? l.target.id : l.target;
        if (!pmap.has(tgt)) pmap.set(tgt, []);
        pmap.get(tgt).push(src);
      });
      return pmap;
    }

    function collectAncestors(id, parents, acc = new Set()) {
      if (acc.has(id)) return acc;
      acc.add(id);
      const ps = parents.get(id) || [];
      ps.forEach(p => collectAncestors(p, parents, acc));
      return acc;
    }

    // Highlight ancestors and connecting links
    function highlightAncestry(selectedId) {
      const parents = buildParents();
      const ancestorIds = collectAncestors(selectedId, parents);
      node.classed("ancestor", d => ancestorIds.has(d.id));
      link.classed("ancestor-link", l => {
        const tgt = l.target.id ? l.target.id : l.target;
        return ancestorIds.has(tgt);
      });
    }

    // Search behavior: list matching quests; clicking focuses them. No graph recolor.
    search.addEventListener("input", (e) => {
      const term = e.target.value.trim().toLowerCase();
      searchResults.innerHTML = "";
      if (!term) return; // empty stops filtering
      const matches = nodes.filter(n => n.name.toLowerCase().includes(term)).slice(0, 25);
      matches.forEach(n => {
        const pill = document.createElement("span");
        pill.className = "pill";
        pill.textContent = n.name;
        pill.addEventListener("click", () => focusNode(n));
        searchResults.appendChild(pill);
      });
    });

    // Preselect first node
    selectNode(nodes[0]);
    highlightAncestry(nodes[0].id);
  </script>
</body>
</html>
"""


def normalize_list(raw: str) -> List[str]:
    if not raw or pd.isna(raw):
        return []
    parts = [p.strip() for p in str(raw).split("|")]
    return [p for p in parts if p]


def build_graph(df: pd.DataFrame, link_map: Dict[str, str]):
    nodes: Dict[str, Dict] = {}
    link_set = set()

    def clean_value(val):
        return None if val is None or (isinstance(val, float) and pd.isna(val)) else val

    def ensure_node(name: str, row_data=None):
        if name not in nodes:
            nodes[name] = {
                "id": name,
                "name": name,
                "location": None,
                "given_by": None,
                "url": link_map.get(name),
                "dialogue": [],
                "objectives": [],
                "rewards": [],
                "previous": [],
                "leads_to": [],
            }
        node = nodes[name]
        if row_data is not None:
            if not node.get("location"):
                node["location"] = clean_value(row_data.get("location"))
            if not node.get("given_by"):
                node["given_by"] = clean_value(row_data.get("given_by"))
            if not node.get("url"):
                node["url"] = link_map.get(name)
            if not node.get("dialogue"):
                node["dialogue"] = normalize_list(row_data.get("dialogue"))
            if not node.get("objectives"):
                node["objectives"] = normalize_list(row_data.get("objectives"))
            if not node.get("rewards"):
                node["rewards"] = normalize_list(row_data.get("rewards"))
            if not node.get("previous"):
                node["previous"] = normalize_list(row_data.get("previous"))
            if not node.get("leads_to"):
                node["leads_to"] = normalize_list(row_data.get("leads_to"))
        return node

    links = []
    for _, row in df.iterrows():
        quest_name = row["name"]
        ensure_node(quest_name, row)

        for prev in normalize_list(row.get("previous")):
            ensure_node(prev)
            link_set.add((prev, quest_name))

        for nxt in normalize_list(row.get("leads_to")):
            ensure_node(nxt)
            link_set.add((quest_name, nxt))

    links = [{"source": s, "target": t} for (s, t) in sorted(link_set)]

    # Level assignment (left-to-right) using a topological-style pass; cycles are pushed minimally.
    indegree = {n: 0 for n in nodes}
    for s, t in link_set:
        indegree[t] = indegree.get(t, 0) + 1
        indegree.setdefault(s, 0)

    levels = {n: 0 for n in nodes}
    queue = [n for n, deg in indegree.items() if deg == 0]

    while queue:
        cur = queue.pop(0)
        cur_level = levels[cur]
        for s, t in link_set:
            if s != cur:
                continue
            if levels.get(t, 0) < cur_level + 1:
                levels[t] = cur_level + 1
            indegree[t] -= 1
            if indegree[t] == 0:
                queue.append(t)

    # One more relaxation pass to handle cycles gracefully.
    for _ in range(len(nodes)):
        updated = False
        for s, t in link_set:
            if levels[t] < levels[s] + 1:
                levels[t] = levels[s] + 1
                updated = True
        if not updated:
            break

    for name, node in nodes.items():
        node["level"] = levels.get(name, 0)

    return list(nodes.values()), links


def main():
    df = pd.read_csv("quests.csv", encoding="utf-8")

    link_map: Dict[str, str] = {}
    link_file = Path("quest_links.json")
    if link_file.exists():
        for entry in json.loads(link_file.read_text(encoding="utf-8")):
            link_map[entry.get("title")] = entry.get("href")

    nodes, links = build_graph(df, link_map)

    html = (
        HTML_TEMPLATE
        .replace("__NODES__", json.dumps(nodes, ensure_ascii=False))
        .replace("__LINKS__", json.dumps(links, ensure_ascii=False))
    )

    out_path = Path("quest_tree.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated interactive quest tree at {out_path}")


if __name__ == "__main__":
    main()
