from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Dict, List
from urllib.parse import quote

import pandas as pd


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Tarkov Quest Tree</title>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,400,0,0" />
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
      --status-completed: #22c55e;
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
      padding-bottom: 26px;
    }
    #chart { position: relative; border-right: 1px solid #1f2937; }
    #panel {
      background: var(--panel);
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: -6px 0 24px rgba(0,0,0,0.4);
      overflow-y: auto;
      padding-bottom: 36px;
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
    #card { display: flex; flex-direction: column; gap: 10px; }
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
    #rewards-box .rewards-body { display: flex; flex-direction: column; gap: 10px; }
    #rewards-box .reward-group { display: flex; flex-direction: column; gap: 4px; }
    #rewards-box .reward-label {
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }
    #legend { font-size: 12px; color: var(--muted); }
    #open-link { padding: 10px 12px; border: 1px solid var(--accent); background: rgba(59,130,246,0.15); color: #bfdbfe; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 4px; align-self: flex-start; display: inline-flex; text-decoration: none; }
    #open-link.is-disabled { opacity: 0.4; cursor: not-allowed; border-color: var(--stroke); pointer-events: none; }
    svg { width: 100%; height: 100%; background: transparent; }
    .node { cursor: pointer; }
    .node circle.core { stroke: var(--stroke); stroke-width: 1.5; }
    .node circle.status-ring { fill: none; stroke-width: 4; opacity: 0; }
    .node circle.important-ring {
      fill: none;
      stroke: #f59e0b;
      stroke-width: 4.5;
      opacity: 0;
      filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.8));
    }
    .node circle.available-ring {
      fill: none;
      stroke: #38bdf8;
      stroke-width: 4;
      opacity: 0;
      filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.75));
    }
    .node text { pointer-events: none; font-size: 12px; fill: var(--text); text-shadow: 0 1px 2px rgba(0,0,0,0.6); }
    .node .level-badge { font-size: 9px; font-weight: 700; fill: #f8fafc; stroke: #0b1223; stroke-width: 0.5px; paint-order: stroke; text-shadow: 0 1px 2px rgba(0,0,0,0.6); }
    .node .unlock-badge {
      font-size: 18px;
      font-weight: 800;
      fill: #f59e0b;
      stroke: #0b1223;
      stroke-width: 2;
      paint-order: stroke;
      pointer-events: none;
    }
    .node.is-important circle.important-ring { opacity: 1; }
    .node.is-important circle.core { stroke: #fbbf24; stroke-width: 3; }
    .node.is-important text { fill: #fef3c7; }
    .node.is-available circle.available-ring { opacity: 1; }
    .link { stroke: rgba(148,163,184,0.5); stroke-width: 1.6px; }
    .node.selected circle.core { stroke: var(--accent-2); stroke-width: 3; }
    .node.ancestor circle.core { stroke: #38bdf8; stroke-width: 3; filter: drop-shadow(0 0 6px rgba(56,189,248,0.75)); }
    .link.ancestor-link { stroke: rgba(56,189,248,0.85); stroke-width: 2.4px; }
    .node.descendant circle.core { stroke: #f87171; stroke-width: 3; filter: drop-shadow(0 0 6px rgba(248,113,113,0.75)); }
    .link.descendant-link { stroke: rgba(248,113,113,0.85); stroke-width: 2.4px; }
    .node.is-completed circle.core { fill: #334155; stroke: #475569; }
    .node.is-completed text { fill: #94a3b8; text-shadow: none; }
    .node.is-completed .level-badge { fill: #e2e8f0; stroke: #1f2937; }
    .node.is-filtered { opacity: 0.28; }
    .link.is-filtered { stroke: rgba(148,163,184,0.15); }
    #search-row { display: flex; align-items: center; gap: 8px; }
    #filter-toggle {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      border: 1px solid var(--stroke);
      background: #0b1223;
      color: var(--text);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    #filter-toggle.is-active { border-color: var(--accent); color: #bfdbfe; }
    #search { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--stroke); background: #0b1223; color: var(--text); }
    #filter-panel {
      display: none;
      flex-direction: column;
      gap: 12px;
      padding: 10px;
      border-radius: 10px;
      border: 1px solid var(--stroke);
      background: #0b1223;
    }
    #filter-panel.is-open { display: flex; }
    .filter-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
    .filter-field { display: flex; flex-direction: column; gap: 6px; }
    .filter-field label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.6px; }
    .filter-field select {
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--stroke);
      background: #0f172a;
      color: var(--text);
      font-size: 12px;
    }
    #filter-clear {
      align-self: flex-end;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--stroke);
      background: #0f172a;
      color: var(--text);
      cursor: pointer;
      font-size: 12px;
    }
    .filter-tags { display: flex; flex-wrap: wrap; gap: 6px; }
    .filter-tag {
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--stroke);
      background: #0f172a;
      color: var(--text);
      cursor: pointer;
      font-size: 11px;
    }
    .filter-tag.is-active { border-color: var(--accent); color: #bfdbfe; }
    .range-field { flex: 1 1 260px; }
    .range-values { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); }
    .range-wrap { position: relative; height: 28px; }
    .range-track {
      position: absolute;
      left: 0;
      right: 0;
      top: 12px;
      height: 4px;
      border-radius: 999px;
      background: #111827;
    }
    .range-fill {
      position: absolute;
      top: 12px;
      height: 4px;
      border-radius: 999px;
      background: var(--accent);
    }
    .range-wrap input[type="range"] {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 28px;
      margin: 0;
      background: none;
      pointer-events: none;
      -webkit-appearance: none;
    }
    .range-wrap input[type="range"].range-min { z-index: 3; }
    .range-wrap input[type="range"].range-max { z-index: 4; }
    .range-wrap input[type="range"]::-webkit-slider-runnable-track { height: 28px; background: transparent; }
    .range-wrap input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--accent);
      border: 2px solid #0b1223;
      margin-top: 8px;
      pointer-events: auto;
      cursor: pointer;
    }
    .range-wrap input[type="range"]::-moz-range-track { height: 28px; background: transparent; }
    .range-wrap input[type="range"]::-moz-range-thumb {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--accent);
      border: 2px solid #0b1223;
      pointer-events: auto;
      cursor: pointer;
    }
    #search-modes { display: flex; gap: 8px; }
    #search-modes .mode-btn { padding: 6px 10px; border-radius: 8px; border: 1px solid var(--stroke); background: #0b1223; color: var(--text); cursor: pointer; font-size: 12px; }
    #search-modes .mode-btn.active { border-color: var(--accent); color: #bfdbfe; }
    #search-results { display: flex; flex-direction: column; gap: 10px; padding: 4px 0 8px; }
    #search-results .item-group { border: 1px solid var(--stroke); border-radius: 8px; padding: 8px; background: #0b1223; }
    #search-results .item-title { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
    #search-results .pill-row { display: flex; flex-wrap: wrap; gap: 6px; }
    #search-results .pill { padding: 6px 10px; border-radius: 999px; border: 1px solid var(--stroke); background: #0b1223; color: var(--text); cursor: pointer; font-size: 12px; }
    #search-results .pill:hover { border-color: var(--accent); color: #bfdbfe; }
    #search-results .pill.is-filtered { opacity: 0.35; filter: grayscale(0.8); }
    #search-results .item-group.is-filtered { opacity: 0.4; }
    #footer-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 10px;
      padding: 4px 12px;
      background: var(--panel);
      border-top: 1px solid var(--stroke);
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.1px;
    }
    #footer-bar a {
      color: #38bdf8;
      text-decoration: none;
    }
    #footer-bar a:hover {
      text-decoration: underline;
    }
    #progress-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
    .progress-btn {
      width: 32px;
      height: 32px;
      padding: 0;
      border-radius: 8px;
      border: 1px solid var(--stroke);
      background: #0b1223;
      color: var(--text);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    .progress-btn.active { border-color: var(--accent); color: #bfdbfe; box-shadow: 0 0 10px rgba(59,130,246,0.3); }
    #important-toggle { border-color: #92400e; color: #f59e0b; }
    #important-toggle.active {
      border-color: #f59e0b;
      color: #fef3c7;
      box-shadow: 0 0 12px rgba(245, 158, 11, 0.45);
    }
    .file-input { position: relative; overflow: hidden; display: inline-flex; align-items: center; justify-content: center; }
    .file-input input {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }
    #progress-meta { display: flex; flex-wrap: wrap; gap: 10px; }
    #progress-current { margin: 0; font-size: 11px; color: var(--muted); }
    #progress-message { min-height: 14px; font-size: 11px; color: var(--muted); }
    #progress-message[data-tone="success"] { color: #86efac; }
    #progress-message[data-tone="error"] { color: #fca5a5; }
    .material-symbols-outlined {
      font-size: 18px;
      line-height: 1;
      font-variation-settings: "opsz" 20, "wght" 400, "FILL" 0, "GRAD" 0;
    }
  </style>
</head>
<body>
  <div id="chart"></div>
  <div id="panel">
    <div id="progress-toolbar">
      <button class="progress-btn" data-status="none" aria-label="Not completed" title="Not completed">
        <span class="material-symbols-outlined" aria-hidden="true">check_box_outline_blank</span>
      </button>
      <button class="progress-btn" data-status="completed" aria-label="Completed" title="Completed">
        <span class="material-symbols-outlined" aria-hidden="true">check_box</span>
      </button>
      <button class="progress-btn" id="important-toggle" aria-label="Important quest" title="Important quest">
        <span class="material-symbols-outlined" aria-hidden="true">priority_high</span>
      </button>
      <button class="progress-btn" id="export-progress" aria-label="Export progress" title="Export JSON">
        <span class="material-symbols-outlined" aria-hidden="true">file_upload</span>
      </button>
      <label class="progress-btn file-input" aria-label="Import progress" title="Import JSON">
        <input id="import-progress" type="file" accept="application/json" />
        <span class="material-symbols-outlined" aria-hidden="true">file_download</span>
      </label>
      <button class="progress-btn" id="clear-progress" aria-label="Clear all progress" title="Clear all progress">
        <span class="material-symbols-outlined" aria-hidden="true">delete</span>
      </button>
    </div>
    <div id="progress-meta">
      <span id="progress-current">Status: Not completed</span>
      <span id="progress-message" data-tone="info">Stored locally in your browser.</span>
    </div>
    <div id="search-row">
      <button id="filter-toggle" aria-label="Filters" title="Filters">
        <span class="material-symbols-outlined" aria-hidden="true">filter_alt</span>
      </button>
      <input id="search" placeholder="Search quests..." />
    </div>
    <div id="filter-panel">
      <div class="filter-row">
        <div class="filter-field">
          <label for="filter-trader">Trader</label>
          <select id="filter-trader"></select>
        </div>
        <div class="filter-field">
          <label for="filter-location">Map</label>
          <select id="filter-location"></select>
        </div>
        <button id="filter-clear">Clear</button>
      </div>
      <div class="filter-row">
        <div class="filter-field">
          <label>Unlocks</label>
          <div class="filter-tags">
            <button class="filter-tag" data-unlock="purchase">Purchase unlock</button>
            <button class="filter-tag" data-unlock="barter">Barter unlock</button>
            <button class="filter-tag" data-unlock="craft">Crafting unlock</button>
          </div>
        </div>
        <div class="filter-field range-field">
          <label>XP reward</label>
          <div class="range-values">
            <span id="xp-min-label">0</span>
            <span id="xp-max-label">0</span>
          </div>
          <div class="range-wrap">
            <div class="range-track"></div>
            <div class="range-fill" id="xp-range-fill"></div>
            <input class="range-min" id="xp-range-min" type="range" min="0" max="0" value="0" step="100" />
            <input class="range-max" id="xp-range-max" type="range" min="0" max="0" value="0" step="100" />
          </div>
        </div>
      </div>
    </div>
    <div id="search-modes">
      <button class="mode-btn active" data-mode="name">Name</button>
      <button class="mode-btn" data-mode="reward">Reward</button>
      <button class="mode-btn" data-mode="unlock">Unlocks</button>
    </div>
    <div id="search-results"></div>
    <div id="card">
      <h1>Select a quest</h1>
      <div class="meta"></div>
      <a id="open-link" class="primary" target="_blank" rel="noopener noreferrer">Open wiki page</a>
      <div class="section" id="objectives-box"><h3>Objectives</h3><ul></ul></div>
      <div class="section" id="rewards-box"><h3>Rewards</h3><div class="rewards-body"></div></div>
      <div class="section" id="requirements-box"><h3>Requirements</h3><ul></ul></div>
      <div class="section" id="previous-box"><h3>Previous</h3><p>-</p></div>
      <div class="section" id="leads-box"><h3>Leads to</h3><p>-</p></div>
    </div>
  </div>
  <div id="footer-bar">
    Scraped for Tarkov 1.0.1.0.42625 — missing quest info? Contact me or fork the repo at
    <a href="https://github.com/denecity/tarkov-tree" target="_blank" rel="noopener noreferrer">github.com/denecity/tarkov-tree</a>
  </div>

  <script>
    // Raw data
    const nodes = __NODES__;
    const links = __LINKS__.map(l => ({ source: l.source, target: l.target }));
    const nodesById = new Map(nodes.map(n => [n.id, n]));
    const STORAGE_KEY = "tarkov-quest-progress";
    const PROGRESS_ENABLED_KEY = "tarkov-quest-progress-enabled";
    const IMPORTANT_KEY = "tarkov-quest-important";
    const STATUS_LABELS = {
      none: "Not completed",
      completed: "Completed"
    };
    const STATUS_COLORS = {
      completed: "var(--status-completed)"
    };
    const STATUS_ALIASES = {
      completed: "completed",
      complete: "completed",
      done: "completed",
      finished: "completed",
      none: "none",
      "not_completed": "none",
      "not started": "none",
      "not_started": "none",
      "in_progress": "none",
      "blocked": "none"
    };

    function normalizeStatus(raw) {
      if (!raw) return "none";
      const cleaned = String(raw).toLowerCase().replace(/\\s+/g, "_").replace(/-+/g, "_");
      return STATUS_ALIASES[cleaned] || "none";
    }

    function loadProgress() {
      try {
        const enabled = localStorage.getItem(PROGRESS_ENABLED_KEY) === "true";
        if (!enabled) return new Map();
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return new Map();
        const parsed = JSON.parse(raw);
        const statuses = parsed && typeof parsed === "object" && parsed.statuses ? parsed.statuses : parsed;
        if (!statuses || typeof statuses !== "object") return new Map();
        const map = new Map();
        Object.entries(statuses).forEach(([id, status]) => {
          const normalized = normalizeStatus(status);
          if (normalized !== "none") {
            map.set(id, normalized);
          }
        });
        return map;
      } catch (_) {
        return new Map();
      }
    }

    function loadImportant() {
      try {
        const raw = localStorage.getItem(IMPORTANT_KEY);
        if (!raw) return new Set();
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return new Set();
        return new Set(parsed);
      } catch (_) {
        return new Set();
      }
    }

    function saveImportant() {
      try {
        localStorage.setItem(IMPORTANT_KEY, JSON.stringify(Array.from(importantSet)));
      } catch (_) {
        // Ignore storage failures (private mode, quota).
      }
    }

    function isImportant(id) {
      return importantSet.has(id);
    }

    function toggleImportant(id) {
      if (!id) return;
      if (importantSet.has(id)) {
        importantSet.delete(id);
      } else {
        importantSet.add(id);
      }
      saveImportant();
      applyImportantToNode(id);
      updateImportantButton();
    }

    function enableProgressLoading() {
      try {
        localStorage.setItem(PROGRESS_ENABLED_KEY, "true");
      } catch (_) {
        // Ignore storage failures (private mode, quota).
      }
    }

    function buildExportPayload(progress) {
      return {
        version: 1,
        updatedAt: new Date().toISOString(),
        statuses: Object.fromEntries(progress)
      };
    }

    let progressMap = loadProgress();
    let importantSet = loadImportant();
    let availableSet = new Set();

    function statusFor(id) {
      return progressMap.get(id) || "none";
    }

    function statusColor(status) {
      return STATUS_COLORS[status] || "transparent";
    }

    const XP_RE = /\\bexp\\b/i;
    const REP_RE = /\\bRep\\b/i;
    const REP_FALLBACK_RE = /^[A-Za-z][A-Za-z\\s-]+\\s*[+-]\\d/;
    const MONEY_RE = /\\b(Roubles|Rubles|Dollars|Euros)\\b/i;
    const UNLOCK_RE = /^Unlocks\\b/i;
    const ITEM_RE = /^\\d+\\s*[x\\u00d7]\\s*/i;
    const ITEM_COUNT_RE = /^\\d[\\d,]*\\s+\\S+/;

    function rewardHasUnlocks(rewards) {
      return (rewards || []).some(reward => UNLOCK_RE.test(reward || ""));
    }

    function isAvailable(id) {
      return availableSet.has(id);
    }

    function saveProgress() {
      try {
        const payload = buildExportPayload(progressMap);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      } catch (_) {
        // Ignore storage failures (private mode, quota).
      }
    }

    const margin = 100;
    const columnGap = 220;
    const height = window.innerHeight;
    const width = Math.max(window.innerWidth * 0.65, margin * 2 + columnGap * 8);

    // Initial positions based on level, random y to spread vertically
    function lockableRoot(n) {
      return (n.level || 0) === 0 && n.leads_to && n.leads_to.length > 0;
    }

    nodes.forEach(n => {
      n.x = margin + (n.level || 0) * columnGap + (Math.random() - 0.5) * 20;
      n.y = margin + (Math.random() * (height - 2 * margin));
      if (lockableRoot(n)) {
        n.fx = margin; // lock x for root nodes that lead somewhere
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
      .classed("has-unlocks", d => rewardHasUnlocks(d.rewards))
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    node.append("circle")
      .attr("class", "available-ring")
      .attr("r", 20)
      .attr("opacity", d => isAvailable(d.id) ? 1 : 0);

    node.append("circle")
      .attr("class", "important-ring")
      .attr("r", 24)
      .attr("opacity", d => isImportant(d.id) ? 1 : 0);

    node.append("circle")
      .attr("class", "status-ring")
      .attr("r", 18)
      .attr("stroke", d => statusColor(statusFor(d.id)))
      .attr("opacity", d => statusFor(d.id) === "none" ? 0 : 1);

    node.append("circle")
      .attr("class", "core")
      .attr("r", 12)
      .attr("fill", d => colorByTrader(d.given_by));

    node.append("text")
      .attr("class", "unlock-badge")
      .attr("x", 9)
      .attr("y", -8)
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .attr("opacity", d => rewardHasUnlocks(d.rewards) ? 1 : 0)
      .text("+");

    node.append("text")
      .attr("class", "level-badge")
      .attr("text-anchor", "middle")
      .attr("dy", "4")
      .text(d => d.required_level ? d.required_level : "");

    node.append("text")
      .attr("x", 12)
      .attr("y", 4)
      .text(d => d.name);

    node.on("click", (_, d) => {
      selectNode(d);
      highlightAncestry(d.id);
    });
    applyProgressToNodes();
    applyImportantToNodes();

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
      .force("collide", d3.forceCollide(18))
      .force("x", d3.forceX(d => margin + (d.level || 0) * columnGap).strength(d => (d.level || 0) === 0 ? 1 : 0.6))
      .force("y", d3.forceY(height / 2).strength(0.02))
      .force("rightBias", forceRightBias(0.22, 90))
      .velocityDecay(0.42)
      .alpha(1)
      .on("tick", ticked);

    const SETTLE_ALPHA = 0.02;
    const SETTLE_VELOCITY = 0.03;
    const SETTLE_TICKS = 24;
    let settleCount = 0;
    let isSettled = false;
    let dragCount = 0;

    let coolTimer = null;
    function warmup() {
      isSettled = false;
      settleCount = 0;
      simulation.alpha(Math.max(simulation.alpha(), 0.45)).alphaTarget(0.3).restart();
      if (coolTimer) clearTimeout(coolTimer);
      coolTimer = setTimeout(() => simulation.alphaTarget(0), 20000);
    }

    function maxVelocity() {
      let max = 0;
      nodes.forEach(n => {
        const vx = Math.abs(n.vx || 0);
        const vy = Math.abs(n.vy || 0);
        const v = vx + vy;
        if (v > max) max = v;
      });
      return max;
    }

    function checkSettled() {
      if (dragCount > 0) {
        settleCount = 0;
        isSettled = false;
        return;
      }
      if (simulation.alpha() > SETTLE_ALPHA) {
        settleCount = 0;
        isSettled = false;
        return;
      }
      const maxV = maxVelocity();
      if (maxV < SETTLE_VELOCITY) {
        settleCount += 1;
        if (settleCount >= SETTLE_TICKS && !isSettled) {
          isSettled = true;
          simulation.alphaTarget(0);
          simulation.stop();
        }
      } else {
        settleCount = 0;
        isSettled = false;
      }
    }

    function ticked() {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      node.attr("transform", d => `translate(${d.x},${d.y})`);
      checkSettled();
    }

    function dragstarted(event) {
      if (!event.active) simulation.alphaTarget(0.2).restart();
      dragCount += 1;
      isSettled = false;
      settleCount = 0;
      if (lockableRoot(event.subject)) {
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
      dragCount = Math.max(0, dragCount - 1);
      if (lockableRoot(event.subject)) {
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
    let selectedNode = null;
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

    function setRewards(list) {
      const container = document.querySelector("#rewards-box .rewards-body");
      if (!container) return;
      container.innerHTML = "";
      if (!list || !list.length) {
        const empty = document.createElement("p");
        empty.textContent = "-";
        container.appendChild(empty);
        return;
      }

      const buckets = {
        xp: [],
        rep: [],
        money: [],
        items: [],
        unlocks: [],
        other: [],
      };

      list.forEach((raw) => {
        const reward = (raw || "").trim();
        if (!reward) return;
        if (UNLOCK_RE.test(reward)) {
          buckets.unlocks.push(reward);
        } else if (XP_RE.test(reward)) {
          buckets.xp.push(reward);
        } else if (REP_RE.test(reward) || REP_FALLBACK_RE.test(reward)) {
          buckets.rep.push(reward);
        } else if (MONEY_RE.test(reward)) {
          buckets.money.push(reward);
        } else if (ITEM_RE.test(reward) || ITEM_COUNT_RE.test(reward)) {
          buckets.items.push(reward);
        } else {
          buckets.other.push(reward);
        }
      });

      const groups = [
        { key: "xp", label: "XP reward" },
        { key: "rep", label: "Trader rep" },
        { key: "money", label: "Money reward" },
        { key: "items", label: "Item rewards" },
        { key: "unlocks", label: "Item unlocks" },
        { key: "other", label: "Other rewards" },
      ];

      let added = 0;
      groups.forEach(({ key, label }) => {
        const items = buckets[key];
        if (!items.length) return;
        const groupEl = document.createElement("div");
        groupEl.className = "reward-group";
        const labelEl = document.createElement("div");
        labelEl.className = "reward-label";
        labelEl.textContent = label;
        const listEl = document.createElement("ul");
        items.forEach((item) => {
          const li = document.createElement("li");
          li.textContent = item;
          listEl.appendChild(li);
        });
        groupEl.appendChild(labelEl);
        groupEl.appendChild(listEl);
        container.appendChild(groupEl);
        added += 1;
      });

      if (!added) {
        const empty = document.createElement("p");
        empty.textContent = "-";
        container.appendChild(empty);
      }
    }

    function selectNode(d) {
      selectedNode = d;
      node.classed("selected", n => n.id === d.id);
      card.querySelector("h1").textContent = d.name;
      card.querySelector(".meta").innerHTML = `
        <span class="chip">Given by: ${d.given_by || "-"}</span>
        <span class="chip">Location: ${d.location || "-"}</span>
      `;
      openLinkBtn.classList.toggle("is-disabled", !d.url);
      openLinkBtn.href = d.url || "#";
      openLinkBtn.target = d.url ? "_blank" : "_self";
      openLinkBtn.rel = d.url ? "noopener noreferrer" : "";
      openLinkBtn.onclick = (e) => {
        if (!d.url) e.preventDefault();
      };
      setList("objectives-box", d.objectives);
      setRewards(d.rewards);
      setList("requirements-box", d.requirements);
      setLinks("previous-box", d.previous);
      setLinks("leads-box", d.leads_to);
      updateProgressButtons();
      updateImportantButton();
    }

    const search = document.getElementById("search");
    const searchResults = document.getElementById("search-results");
    const searchModeButtons = Array.from(document.querySelectorAll("#search-modes .mode-btn"));
    const openLinkBtn = document.getElementById("open-link");
    const progressButtons = Array.from(document.querySelectorAll("#progress-toolbar .progress-btn[data-status]"));
    const progressCurrent = document.getElementById("progress-current");
    const progressMessage = document.getElementById("progress-message");
    const exportProgressBtn = document.getElementById("export-progress");
    const importProgressInput = document.getElementById("import-progress");
    const clearProgressBtn = document.getElementById("clear-progress");
    const importantToggleBtn = document.getElementById("important-toggle");
    const filterToggleBtn = document.getElementById("filter-toggle");
    const filterPanel = document.getElementById("filter-panel");
    const filterTrader = document.getElementById("filter-trader");
    const filterLocation = document.getElementById("filter-location");
    const filterClearBtn = document.getElementById("filter-clear");
    const unlockTagButtons = Array.from(document.querySelectorAll(".filter-tag[data-unlock]"));
    const xpRangeMin = document.getElementById("xp-range-min");
    const xpRangeMax = document.getElementById("xp-range-max");
    const xpMinLabel = document.getElementById("xp-min-label");
    const xpMaxLabel = document.getElementById("xp-max-label");
    const xpRangeFill = document.getElementById("xp-range-fill");
    let searchMode = "name";
    const filterState = { trader: "all", location: "all", unlocks: new Set(), xpMin: null, xpMax: null };
    const XP_SLIDER_MIN = 0;
    const XP_SLIDER_MAX = 100000;
    const xpBounds = { min: XP_SLIDER_MIN, max: XP_SLIDER_MAX };

    function setProgressMessage(text, tone = "info") {
      if (!progressMessage) return;
      progressMessage.textContent = text;
      progressMessage.dataset.tone = tone;
    }

    function updateProgressButtons() {
      if (!progressButtons.length) return;
      const status = selectedNode ? statusFor(selectedNode.id) : "none";
      progressButtons.forEach(btn => {
        btn.classList.toggle("active", btn.dataset.status === status);
      });
      if (progressCurrent) {
        progressCurrent.textContent = `Status: ${STATUS_LABELS[status] || STATUS_LABELS.none}`;
      }
    }

    function buildFilterOptions(selectEl, values, includeUnknown = false) {
      if (!selectEl) return;
      const current = selectEl.value || "all";
      selectEl.innerHTML = "";
      const allOpt = document.createElement("option");
      allOpt.value = "all";
      allOpt.textContent = "All";
      selectEl.appendChild(allOpt);
      if (includeUnknown) {
        const unknownOpt = document.createElement("option");
        unknownOpt.value = "unknown";
        unknownOpt.textContent = "Unknown";
        selectEl.appendChild(unknownOpt);
      }
      values.forEach((val) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent = val;
        selectEl.appendChild(opt);
      });
      if (Array.from(selectEl.options).some(opt => opt.value === current)) {
        selectEl.value = current;
      }
    }

    function parseLocationList(raw) {
      if (!raw) return [];
      return String(raw)
        .split(",")
        .map(part => part.trim())
        .filter(Boolean);
    }

    function parseXpReward(rewards) {
      if (!rewards) return null;
      for (const reward of rewards) {
        const match = String(reward).match(/([0-9][0-9,]*)\\s*EXP/i);
        if (match) {
          const value = parseInt(match[1].replace(/,/g, ""), 10);
          if (!Number.isNaN(value)) return value;
        }
      }
      return null;
    }

    function unlockTypesFor(rewards) {
      const types = new Set();
      if (!rewards) return types;
      rewards.forEach((reward) => {
        const match = String(reward).match(/^Unlocks\\s+(purchase|barter|craft)/i);
        if (match) {
          types.add(match[1].toLowerCase());
        }
      });
      return types;
    }

    function formatXpValue(value) {
      if (value == null) return "-";
      if (value >= XP_SLIDER_MAX) return "100000+";
      return value.toLocaleString("en-US");
    }

    function updateXpTrack(minValue, maxValue, bounds) {
      if (!xpRangeFill || !bounds) return;
      const span = bounds.max - bounds.min || 1;
      const minPercent = ((minValue - bounds.min) / span) * 100;
      const maxPercent = ((maxValue - bounds.min) / span) * 100;
      xpRangeFill.style.left = `${minPercent}%`;
      xpRangeFill.style.width = `${Math.max(0, maxPercent - minPercent)}%`;
    }

    function updateXpState(fromInput, bounds) {
      if (!xpRangeMin || !xpRangeMax || !bounds) return;
      let minValue = parseInt(xpRangeMin.value, 10);
      let maxValue = parseInt(xpRangeMax.value, 10);
      if (Number.isNaN(minValue)) minValue = bounds.min;
      if (Number.isNaN(maxValue)) maxValue = bounds.max;
      if (minValue > maxValue) {
        if (fromInput === xpRangeMin) {
          maxValue = minValue;
        } else {
          minValue = maxValue;
        }
      }
      xpRangeMin.value = String(minValue);
      xpRangeMax.value = String(maxValue);
      filterState.xpMin = minValue;
      filterState.xpMax = maxValue;
      if (minValue >= maxValue - 100) {
        xpRangeMin.style.zIndex = "5";
      } else {
        xpRangeMin.style.zIndex = "3";
      }
      xpRangeMax.style.zIndex = "4";
      if (xpMinLabel) xpMinLabel.textContent = formatXpValue(minValue);
      if (xpMaxLabel) xpMaxLabel.textContent = formatXpValue(maxValue);
      updateXpTrack(minValue, maxValue, bounds);
    }

    function filterMatches(node) {
      if (!node) return false;
      if (filterState.trader !== "all") {
        if (filterState.trader === "unknown") {
          if (node.given_by) return false;
        } else if (node.given_by !== filterState.trader) {
          return false;
        }
      }
      if (filterState.location !== "all") {
        const locations = parseLocationList(node.location);
        if (filterState.location === "unknown") {
          if (locations.length) return false;
        } else if (!locations.includes(filterState.location)) {
          return false;
        }
      }
      if (filterState.unlocks.size) {
        const unlocks = unlockTypesFor(node.rewards);
        let matchesUnlock = false;
        filterState.unlocks.forEach((type) => {
          if (unlocks.has(type)) matchesUnlock = true;
        });
        if (!matchesUnlock) return false;
      }
      if (filterState.xpMin != null && filterState.xpMax != null) {
        const xp = parseXpReward(node.rewards);
        const boundsActive = filterState.xpMin > xpBounds.min || filterState.xpMax < xpBounds.max;
        if (boundsActive) {
          if (xp == null) return false;
          if (xp < filterState.xpMin || xp > filterState.xpMax) return false;
        }
      }
      return true;
    }

    function applyFilters() {
      node.classed("is-filtered", d => !filterMatches(d));
      link.classed("is-filtered", l => {
        const src = l.source.id ? l.source : nodesById.get(l.source);
        const tgt = l.target.id ? l.target : nodesById.get(l.target);
        return !filterMatches(src) || !filterMatches(tgt);
      });
      renderSearchResults(search.value.trim().toLowerCase());
    }

    function updateImportantButton() {
      if (!importantToggleBtn) return;
      const active = selectedNode ? isImportant(selectedNode.id) : false;
      importantToggleBtn.classList.toggle("active", active);
    }

    function applyImportantToNode(id) {
      const important = isImportant(id);
      node.filter(d => d.id === id)
        .classed("is-important", important)
        .select("circle.important-ring")
        .attr("opacity", important ? 1 : 0);
    }

    function applyImportantToNodes() {
      node.classed("is-important", d => isImportant(d.id));
      node.select("circle.important-ring")
        .attr("opacity", d => isImportant(d.id) ? 1 : 0);
    }

    function computeAvailableSet() {
      const children = buildChildren();
      const completed = new Set();
      nodes.forEach(n => {
        if (statusFor(n.id) === "completed") completed.add(n.id);
      });
      const next = new Set();
      completed.forEach((id) => {
        const targets = children.get(id) || [];
        targets.forEach((childId) => {
          if (!completed.has(childId)) next.add(childId);
        });
      });
      availableSet = next;
    }

    function applyAvailableToNodes() {
      computeAvailableSet();
      node.classed("is-available", d => isAvailable(d.id));
      node.select("circle.available-ring")
        .attr("opacity", d => isAvailable(d.id) ? 1 : 0);
    }

    function applyProgressToNode(id) {
      const status = statusFor(id);
      const target = nodesById.get(id);
      if (target) {
        target.progress = status;
      }
      node.filter(d => d.id === id)
        .classed("is-completed", status === "completed")
        .select("circle.status-ring")
        .attr("stroke", statusColor(status))
        .attr("opacity", status === "none" ? 0 : 1);
      applyAvailableToNodes();
    }

    function applyProgressToNodes() {
      nodes.forEach(n => {
        n.progress = statusFor(n.id);
      });
      node
        .classed("is-completed", d => statusFor(d.id) === "completed")
        ;
      node.select("circle.status-ring")
        .attr("stroke", d => statusColor(statusFor(d.id)))
        .attr("opacity", d => statusFor(d.id) === "none" ? 0 : 1);
      applyAvailableToNodes();
    }

    function setStatus(id, status) {
      enableProgressLoading();
      const normalized = normalizeStatus(status);
      if (normalized === "none") {
        progressMap.delete(id);
      } else {
        progressMap.set(id, normalized);
      }
      saveProgress();
      applyProgressToNode(id);
      updateProgressButtons();
    }

    function replaceProgress(newMap, message) {
      progressMap = newMap;
      saveProgress();
      applyProgressToNodes();
      updateProgressButtons();
      if (message) {
        setProgressMessage(message, "success");
      }
    }

    function importProgressFromText(rawText) {
      try {
        const parsed = JSON.parse(rawText);
        const statuses = parsed && typeof parsed === "object" && parsed.statuses ? parsed.statuses : parsed;
        if (!statuses || typeof statuses !== "object") {
          throw new Error("Invalid progress file.");
        }
        const map = new Map();
        Object.entries(statuses).forEach(([id, status]) => {
          const normalized = normalizeStatus(status);
          if (normalized !== "none") {
            map.set(id, normalized);
          }
        });
        enableProgressLoading();
        replaceProgress(map, "Imported progress JSON.");
      } catch (err) {
        setProgressMessage("Could not import JSON. Check the file format.", "error");
      }
    }

    function exportProgressToFile() {
      const payload = buildExportPayload(progressMap);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "tarkov-progress.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setProgressMessage("Exported progress JSON.", "success");
    }

    searchModeButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        searchMode = btn.dataset.mode;
        searchModeButtons.forEach(b => b.classList.toggle("active", b === btn));
        renderSearchResults(search.value.trim().toLowerCase());
      });
    });

    if (filterToggleBtn && filterPanel) {
      filterToggleBtn.addEventListener("click", () => {
        const isOpen = filterPanel.classList.toggle("is-open");
        filterToggleBtn.classList.toggle("is-active", isOpen);
      });
    }

    if (filterTrader) {
      filterTrader.addEventListener("change", () => {
        filterState.trader = filterTrader.value || "all";
        applyFilters();
      });
    }

    if (filterLocation) {
      filterLocation.addEventListener("change", () => {
        filterState.location = filterLocation.value || "all";
        applyFilters();
      });
    }

    if (unlockTagButtons.length) {
      unlockTagButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const type = btn.dataset.unlock;
          if (!type) return;
          if (filterState.unlocks.has(type)) {
            filterState.unlocks.delete(type);
            btn.classList.remove("is-active");
          } else {
            filterState.unlocks.add(type);
            btn.classList.add("is-active");
          }
          applyFilters();
        });
      });
    }

    if (xpRangeMin && xpRangeMax) {
      xpRangeMin.addEventListener("input", () => {
        updateXpState(xpRangeMin, xpBounds);
        applyFilters();
      });
      xpRangeMax.addEventListener("input", () => {
        updateXpState(xpRangeMax, xpBounds);
        applyFilters();
      });
    }

    if (filterClearBtn) {
      filterClearBtn.addEventListener("click", () => {
        filterState.trader = "all";
        filterState.location = "all";
        if (filterTrader) filterTrader.value = "all";
        if (filterLocation) filterLocation.value = "all";
        filterState.unlocks.clear();
        unlockTagButtons.forEach(btn => btn.classList.remove("is-active"));
        if (xpRangeMin && xpRangeMax) {
          xpRangeMin.value = String(xpBounds.min);
          xpRangeMax.value = String(xpBounds.max);
          updateXpState(xpRangeMax, xpBounds);
        }
        applyFilters();
      });
    }

    progressButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        if (!selectedNode) return;
        setStatus(selectedNode.id, btn.dataset.status);
        const status = normalizeStatus(btn.dataset.status);
        setProgressMessage(`Set to ${STATUS_LABELS[status] || STATUS_LABELS.none}.`, "success");
      });
    });

    if (importantToggleBtn) {
      importantToggleBtn.addEventListener("click", () => {
        if (!selectedNode) return;
        toggleImportant(selectedNode.id);
        const message = isImportant(selectedNode.id) ? "Marked as important." : "Removed importance.";
        setProgressMessage(message, "success");
      });
    }

    if (exportProgressBtn) {
      exportProgressBtn.addEventListener("click", () => exportProgressToFile());
    }

    if (importProgressInput) {
      importProgressInput.addEventListener("change", (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        file.text()
          .then(text => importProgressFromText(text))
          .catch(() => setProgressMessage("Could not read the selected file.", "error"));
        importProgressInput.value = "";
      });
    }

    if (clearProgressBtn) {
      clearProgressBtn.addEventListener("click", () => {
        if (!confirm("Clear all quest progress?")) return;
        replaceProgress(new Map(), "Cleared all progress.");
      });
    }

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

    function buildChildren() {
      const cmap = new Map();
      links.forEach(l => {
        const src = l.source.id ? l.source.id : l.source;
        const tgt = l.target.id ? l.target.id : l.target;
        if (!cmap.has(src)) cmap.set(src, []);
        cmap.get(src).push(tgt);
      });
      return cmap;
    }

    function collectAncestors(id, parents, acc = new Set()) {
      if (acc.has(id)) return acc;
      acc.add(id);
      const ps = parents.get(id) || [];
      ps.forEach(p => collectAncestors(p, parents, acc));
      return acc;
    }

    function collectDescendants(id, children, acc = new Set()) {
      if (acc.has(id)) return acc;
      acc.add(id);
      const cs = children.get(id) || [];
      cs.forEach(c => collectDescendants(c, children, acc));
      return acc;
    }

    // Highlight ancestors (previous) in blue and descendants (leads_to) in red
    function highlightAncestry(selectedId) {
      const parents = buildParents();
      const ancestorIds = collectAncestors(selectedId, parents);
      const children = buildChildren();
      const descendantIds = collectDescendants(selectedId, children);
      node.classed("ancestor", d => ancestorIds.has(d.id));
      node.classed("descendant", d => descendantIds.has(d.id));
      link.classed("ancestor-link", l => {
        const tgt = l.target.id ? l.target.id : l.target;
        return ancestorIds.has(tgt);
      });
      link.classed("descendant-link", l => {
        const src = l.source.id ? l.source.id : l.source;
        const tgt = l.target.id ? l.target.id : l.target;
        return descendantIds.has(src) && descendantIds.has(tgt);
      });
    }

    function rewardMatches(node, term) {
      if (!term) return [];
      const rewards = node.rewards || [];
      const hits = [];
      for (const r of rewards) {
        if (!r.includes("×")) continue;
        const m = r.match(/([0-9]+)\s*×\s*(.+)/);
        const itemName = m ? m[2].trim() : r;
        const count = m ? parseInt(m[1], 10) : 1;
        if (itemName.toLowerCase().includes(term)) {
          hits.push({ item: itemName, count });
        }
      }
      return hits;
    }

    function unlockMatches(node, term) {
          if (!term) return [];
          const rewards = node.rewards || [];
          const hits = [];
          for (const r of rewards) {
            const lower = r.toLowerCase();
            if (!lower.startsWith("unlocks")) continue;
            // Match purchase/barter/craft unlocks and capture the item name and location
            const m = r.match(/^Unlocks\\s+(purchase|barter|craft)\\s+(?:for\\s+|of\\s+)?(.+?)(?:\\s+at\\s+(.+))?$/i);
            if (!m || !m[2]) continue;
            const kind = m[1] ? m[1].toLowerCase() : "unlock";
            const itemName = m[2].trim();
            const place = m[3] ? m[3].trim() : "";
            if (itemName.toLowerCase().includes(term)) {
              hits.push({ item: itemName, count: 1, kind, place });
            }
          }
          return hits;
        }

    function renderSearchResults(term) {
        searchResults.innerHTML = "";
        if (!term) return;
      if (searchMode === "name") {
        const matches = nodes.filter(n => n.name.toLowerCase().includes(term)).slice(0, 25);
        matches.forEach(n => {
          const pill = document.createElement("span");
          pill.className = "pill";
          pill.classList.toggle("is-filtered", !filterMatches(n));
          pill.textContent = n.name;
          pill.addEventListener("click", () => focusNode(n));
          searchResults.appendChild(pill);
        });
        return;
      }

      const groups = new Map(); // item -> [{node, count}]
      const matcher = searchMode === "reward" ? rewardMatches : unlockMatches;
      nodes.forEach(n => {
        matcher(n, term).forEach(hit => {
          if (!groups.has(hit.item)) groups.set(hit.item, []);
          groups.get(hit.item).push({ node: n, count: hit.count, kind: hit.kind, place: hit.place });
        });
      });
      Array.from(groups.entries()).slice(0, 25).forEach(([item, arr]) => {
        const box = document.createElement("div");
        box.className = "item-group";
        const title = document.createElement("div");
        title.className = "item-title";
        title.textContent = item;
        box.appendChild(title);
        const row = document.createElement("div");
        row.className = "pill-row";
        let allFiltered = true;
        arr.forEach(({ node: n, count, kind, place }) => {
          const pill = document.createElement("span");
          pill.className = "pill";
          const filteredOut = !filterMatches(n);
          pill.classList.toggle("is-filtered", filteredOut);
          if (!filteredOut) allFiltered = false;
          const meta = [];
          if (kind) meta.push(kind);
          if (place) meta.push(place);
          const suffix = meta.length ? ` - ${meta.join(" @ ")}` : "";
          pill.textContent = `${n.name} (${count}x)${suffix}`;
          pill.addEventListener("click", () => focusNode(n));
          row.appendChild(pill);
        });
        box.appendChild(row);
        box.classList.toggle("is-filtered", allFiltered);
        searchResults.appendChild(box);
      });
      }

    // Search behavior: list matching quests; clicking focuses them. No graph recolor.
    search.addEventListener("input", (e) => {
      const term = e.target.value.trim().toLowerCase();
      renderSearchResults(term);
    });

    // Preselect first node
    selectNode(nodes[0]);
    highlightAncestry(nodes[0].id);
    warmup();
    const traders = Array.from(new Set(nodes.map(n => n.given_by).filter(Boolean))).sort();
    const locations = Array.from(new Set(nodes.flatMap(n => parseLocationList(n.location)))).sort();
    buildFilterOptions(filterTrader, traders, nodes.some(n => !n.given_by));
    buildFilterOptions(filterLocation, locations, nodes.some(n => !n.location));
    xpBounds.min = XP_SLIDER_MIN;
    xpBounds.max = XP_SLIDER_MAX;
    if (xpRangeMin && xpRangeMax) {
      xpRangeMin.min = String(xpBounds.min);
      xpRangeMin.max = String(xpBounds.max);
      xpRangeMax.min = String(xpBounds.min);
      xpRangeMax.max = String(xpBounds.max);
      xpRangeMin.value = String(xpBounds.min);
      xpRangeMax.value = String(xpBounds.max);
      updateXpState(xpRangeMax, xpBounds);
    } else {
      filterState.xpMin = xpBounds.min;
      filterState.xpMax = xpBounds.max;
      if (xpMinLabel) xpMinLabel.textContent = formatXpValue(xpBounds.min);
      if (xpMaxLabel) xpMaxLabel.textContent = formatXpValue(xpBounds.max);
    }
    applyFilters();
  </script>
</body>
</html>
"""


def normalize_list(raw: str) -> List[str]:
    if not raw or pd.isna(raw):
        return []
    parts = [p.strip() for p in str(raw).split("|")]
    return [p for p in parts if p]


def parse_required_level(requirements: List[str]):
    for req in requirements:
        match = re.search(r"must be level\s*(\d+)", req, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def build_graph(df: pd.DataFrame, link_map: Dict[str, str]):
    nodes: Dict[str, Dict] = {}
    link_set = set()

    def clean_value(val):
        return None if val is None or (isinstance(val, float) and pd.isna(val)) else val

    def ensure_node(name: str, row_data=None):
        # Fallback wiki URL even if quest_links lookup misses a title match.
        def resolved_url(n: str):
            if not n:
                return None
            return link_map.get(n) or f"https://escapefromtarkov.fandom.com/wiki/{quote(n.replace(' ', '_'))}"

        if name not in nodes:
            nodes[name] = {
                "id": name,
                "name": name,
                "location": None,
                "given_by": None,
                "url": resolved_url(name),
                "dialogue": [],
                "requirements": [],
                "required_level": None,
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
                node["url"] = clean_value(row_data.get("url")) or resolved_url(name)
            if not node.get("dialogue"):
                node["dialogue"] = normalize_list(row_data.get("dialogue"))
            if not node.get("requirements"):
                node["requirements"] = normalize_list(row_data.get("requirements"))
            if node.get("required_level") is None:
                node["required_level"] = parse_required_level(node.get("requirements", []))
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

    # Level assignment using multi-source BFS (shortest depth from any root) to avoid runaway levels in cycles.
    indegree = {n: 0 for n in nodes}
    adjacency: Dict[str, List[str]] = {}
    for s, t in link_set:
        indegree[t] = indegree.get(t, 0) + 1
        indegree.setdefault(s, 0)
        adjacency.setdefault(s, []).append(t)

    roots = [n for n, deg in indegree.items() if deg == 0] or list(nodes.keys())
    levels = {n: float("inf") for n in nodes}
    for r in roots:
        levels[r] = 0

    queue = list(roots)
    while queue:
        cur = queue.pop(0)
        cur_level = levels[cur]
        for nxt in adjacency.get(cur, []):
            if cur_level + 1 < levels[nxt]:
                levels[nxt] = cur_level + 1
                queue.append(nxt)

    # Replace inf (isolated nodes) with 0
    for n in levels:
        if levels[n] == float("inf"):
            levels[n] = 0

    for name, node in nodes.items():
        node["level"] = levels.get(name, 0)

    return list(nodes.values()), links


def main():
    df = pd.read_csv("src/quests.csv", encoding="utf-8")

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

    out_path = Path("index.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated interactive quest tree at {out_path}")


if __name__ == "__main__":
    main()
