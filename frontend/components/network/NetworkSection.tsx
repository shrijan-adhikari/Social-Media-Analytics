"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import {
  Network,
  GitBranch,
  ArrowRight,
  AlertTriangle,
  Filter,
  Eye,
  RotateCcw,
  Sliders,
  Calendar,
  X,
  MessageSquare,
  Repeat,
  Heart,
  HelpCircle,
} from "lucide-react";
import {
  NetworkEdgeItem,
  NetworkNodeItem,
  NetworkSummaryResponse,
  TopicNetworkResponse,
  TweetItem,
} from "@/lib/types/api";
import { fetchTweets } from "@/lib/api/client";

interface NetworkSectionProps {
  globalSummary: NetworkSummaryResponse;
  globalNodes: NetworkNodeItem[];
  globalEdges: NetworkEdgeItem[];
  topicNetwork: TopicNetworkResponse | null;
  selectedTopicLabel?: string | null;
  onOpenEvidence?: (metricType: string) => void;
}

// Clarification 6: Deterministic Categorical Community Palette
const CATEGORICAL_COLORS = [
  "#E5B95C", // Gold
  "#00E575", // Green
  "#38BDF8", // Sky
  "#A78BFA", // Purple
  "#FB923C", // Orange
  "#F43F5E", // Rose
  "#2DD4BF", // Teal
  "#818CF8", // Indigo
  "#E879F9", // Fuchsia
  "#A3E635", // Lime
  "#FBBF24", // Amber
  "#60A5FA", // Blue
  "#34D399", // Emerald
  "#F472B6", // Pink
];

function getCategoricalCommunityColor(cid: number | null | undefined): string {
  if (cid === null || cid === undefined || cid < 0) return "#85817B";
  return CATEGORICAL_COLORS[Math.abs(cid) % CATEGORICAL_COLORS.length];
}

export function NetworkSection({
  globalSummary,
  globalNodes,
  globalEdges,
  topicNetwork,
  selectedTopicLabel,
  onOpenEvidence,
}: NetworkSectionProps) {
  // Primary Controls
  const [scopeMode, setScopeMode] = useState<"topic" | "global">("topic");
  const [componentFilter, setComponentFilter] = useState<"largest" | "top5" | "all">("largest");

  // Toggles (Default: isolated nodes and self-loops OFF)
  const [showIsolated, setShowIsolated] = useState(false);
  const [showSelfLoops, setShowSelfLoops] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [showArrows, setShowArrows] = useState(true);
  const [showCrossCommunity, setShowCrossCommunity] = useState(true);

  // Sliders
  const [minWeight, setMinWeight] = useState(1.0);
  const [timeProgress, setTimeProgress] = useState(100); // 0 to 100% of time span

  // Selection & Inspector
  const [selectedNode, setSelectedNode] = useState<NetworkNodeItem | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<NetworkEdgeItem | null>(null);
  const [egoCenterUserId, setEgoCenterUserId] = useState<number | null>(null);
  const [userTweets, setUserTweets] = useState<TweetItem[]>([]);
  const [isLoadingUserTweets, setIsLoadingUserTweets] = useState(false);
  const [showUserTweetsModal, setShowUserTweetsModal] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);

  // Scope Resolution
  const hasTopicNetwork = Boolean(topicNetwork && topicNetwork.available && topicNetwork.run);
  const isViewingGlobal = scopeMode === "global" || !hasTopicNetwork;

  const rawSummary = isViewingGlobal ? globalSummary : topicNetwork!.run!;
  const rawNodes = isViewingGlobal ? globalNodes : topicNetwork!.nodes;
  const rawEdges = isViewingGlobal ? globalEdges : topicNetwork!.edges;

  // Max edge weight for slider
  const maxWeightInDataset = useMemo(() => {
    return Math.max(...rawEdges.map((e) => e.total_weight), 1.0);
  }, [rawEdges]);

  // Compute time bounds for temporal slider
  const { minTimestamp, maxTimestamp } = useMemo(() => {
    const timestamps = rawEdges
      .map((e) => (e.first_observed_at ? new Date(e.first_observed_at).getTime() : null))
      .filter((t): t is number => t !== null);

    if (timestamps.length === 0) return { minTimestamp: 0, maxTimestamp: 0 };
    return {
      minTimestamp: Math.min(...timestamps),
      maxTimestamp: Math.max(...timestamps),
    };
  }, [rawEdges]);

  const effectiveTimeCutoff = useMemo(() => {
    if (minTimestamp === maxTimestamp || timeProgress === 100) return null;
    return minTimestamp + ((maxTimestamp - minTimestamp) * timeProgress) / 100;
  }, [minTimestamp, maxTimestamp, timeProgress]);

  // Connected Component Decomposition
  const components = useMemo(() => {
    // Adjacency map
    const adj = new Map<number, Set<number>>();
    rawNodes.forEach((n) => adj.set(n.user_id, new Set()));

    rawEdges.forEach((e) => {
      if (e.source_user_id !== e.target_user_id) {
        adj.get(e.source_user_id)?.add(e.target_user_id);
        adj.get(e.target_user_id)?.add(e.source_user_id);
      }
    });

    const visited = new Set<number>();
    const compList: number[][] = [];

    rawNodes.forEach((n) => {
      if (!visited.has(n.user_id)) {
        const comp: number[] = [];
        const queue: number[] = [n.user_id];
        visited.add(n.user_id);

        while (queue.length > 0) {
          const curr = queue.shift()!;
          comp.push(curr);
          const neighbors = adj.get(curr) || new Set();
          neighbors.forEach((nbr) => {
            if (!visited.has(nbr)) {
              visited.add(nbr);
              queue.push(nbr);
            }
          });
        }
        compList.push(comp);
      }
    });

    // Sort components by size descending
    compList.sort((a, b) => b.length - a.length);
    return compList;
  }, [rawNodes, rawEdges]);

  // Filtered Nodes & Edges Pipeline
  const { filteredNodes, filteredEdges } = useMemo(() => {
    // 1. Component Filtering
    let allowedUserIds = new Set<number>();
    if (componentFilter === "largest") {
      const largestComp = components[0] || [];
      allowedUserIds = new Set(largestComp);
    } else if (componentFilter === "top5") {
      const top5 = components.slice(0, 5).flat();
      allowedUserIds = new Set(top5);
    } else {
      allowedUserIds = new Set(rawNodes.map((n) => n.user_id));
    }

    // 2. Ego Network Filter
    if (egoCenterUserId !== null) {
      const directNeighbors = new Set<number>([egoCenterUserId]);
      rawEdges.forEach((e) => {
        if (e.source_user_id === egoCenterUserId) directNeighbors.add(e.target_user_id);
        if (e.target_user_id === egoCenterUserId) directNeighbors.add(e.source_user_id);
      });
      allowedUserIds = directNeighbors;
    }

    // 3. Filter Edges
    let visibleEdges = rawEdges.filter((e) => {
      if (!allowedUserIds.has(e.source_user_id) || !allowedUserIds.has(e.target_user_id)) {
        return false;
      }
      // Self loops toggle
      if (!showSelfLoops && e.source_user_id === e.target_user_id) {
        return false;
      }
      // Min weight filter
      if (e.total_weight < minWeight) {
        return false;
      }
      // Temporal filter (Observed Interaction Evolution)
      if (effectiveTimeCutoff !== null && e.first_observed_at) {
        const t = new Date(e.first_observed_at).getTime();
        if (t > effectiveTimeCutoff) return false;
      }
      return true;
    });

    // 4. Cross-community toggle
    const communityLookup = new Map<number, number | null>();
    rawNodes.forEach((n) => communityLookup.set(n.user_id, n.community_id));

    if (!showCrossCommunity) {
      visibleEdges = visibleEdges.filter((e) => {
        const c1 = communityLookup.get(e.source_user_id);
        const c2 = communityLookup.get(e.target_user_id);
        return c1 === c2;
      });
    }

    // 5. Filter Nodes (isolated toggle)
    const connectedInVisibleEdges = new Set<number>();
    visibleEdges.forEach((e) => {
      connectedInVisibleEdges.add(e.source_user_id);
      connectedInVisibleEdges.add(e.target_user_id);
    });

    let visibleNodes = rawNodes.filter((n) => {
      if (!allowedUserIds.has(n.user_id)) return false;
      if (!showIsolated && !connectedInVisibleEdges.has(n.user_id) && egoCenterUserId !== n.user_id) {
        return false;
      }
      return true;
    });

    // Limit visible elements to 200 nodes & 300 edges to maintain 60 FPS
    visibleNodes = visibleNodes.slice(0, 180);
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.user_id));
    visibleEdges = visibleEdges
      .filter((e) => visibleNodeIds.has(e.source_user_id) && visibleNodeIds.has(e.target_user_id))
      .slice(0, 250);

    return { filteredNodes: visibleNodes, filteredEdges: visibleEdges };
  }, [
    rawNodes,
    rawEdges,
    componentFilter,
    components,
    egoCenterUserId,
    showIsolated,
    showSelfLoops,
    minWeight,
    effectiveTimeCutoff,
    showCrossCommunity,
  ]);

  // Derived Rank Context for Selected Node (Clarification 8)
  const nodeRankContext = useMemo(() => {
    if (!selectedNode) return null;
    const sortedPr = [...rawNodes].sort((a, b) => b.pagerank_score - a.pagerank_score);
    const prRank = sortedPr.findIndex((n) => n.user_id === selectedNode.user_id) + 1;

    const sortedBw = [...rawNodes].sort((a, b) => b.betweenness_centrality - a.betweenness_centrality);
    const bwRank = sortedBw.findIndex((n) => n.user_id === selectedNode.user_id) + 1;

    // Derived interaction totals from edges
    let totalReplies = 0;
    let totalMentions = 0;
    let totalReposts = 0;
    let totalQuotes = 0;

    rawEdges.forEach((e) => {
      if (e.source_user_id === selectedNode.user_id || e.target_user_id === selectedNode.user_id) {
        totalReplies += e.reply_count;
        totalMentions += e.mention_count;
        totalReposts += e.repost_count;
        totalQuotes += e.quote_count;
      }
    });

    return {
      prRank,
      bwRank,
      totalCount: rawNodes.length,
      totalReplies,
      totalMentions,
      totalReposts,
      totalQuotes,
    };
  }, [selectedNode, rawNodes, rawEdges]);

  // Fetch Related Tweets when requested
  const handleLoadUserTweets = async (userId: number) => {
    setIsLoadingUserTweets(true);
    setShowUserTweetsModal(true);
    try {
      const res = await fetchTweets({ user_id: userId, page_size: 10 });
      setUserTweets(res.items);
    } catch (err) {
      console.error("Failed to load user tweets:", err);
      setUserTweets([]);
    } finally {
      setIsLoadingUserTweets(false);
    }
  };

  // Cytoscape Instance Lifecycle
  useEffect(() => {
    let isMounted = true;

    async function renderGraph() {
      if (!containerRef.current) return;
      const cytoscape = (await import("cytoscape")).default;

      if (!isMounted) return;

      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }

      if (filteredNodes.length === 0) return;

      const maxPR = Math.max(...filteredNodes.map((n) => n.pagerank_score), 0.001);

      const elements = [
        ...filteredNodes.map((n) => {
          const size = Math.max(18, Math.min(48, (n.pagerank_score / maxPR) * 40 + 16));
          const color = getCategoricalCommunityColor(n.community_id);

          return {
            data: {
              id: n.user_id.toString(),
              label: showLabels ? `@${n.username}` : "",
              color: color,
              size: size,
              nodeData: n,
            },
          };
        }),
        ...filteredEdges.map((e, idx) => {
          const width = Math.max(1.2, Math.min(7, e.total_weight * 1.5));
          const isCross =
            filteredNodes.find((n) => n.user_id === e.source_user_id)?.community_id !==
            filteredNodes.find((n) => n.user_id === e.target_user_id)?.community_id;

          return {
            data: {
              id: `edge_${idx}_${e.source_user_id}_${e.target_user_id}`,
              source: e.source_user_id.toString(),
              target: e.target_user_id.toString(),
              weight: width,
              isCross: isCross,
              edgeData: e,
            },
          };
        }),
      ];

      const cy = cytoscape({
        container: containerRef.current,
        elements: elements,
        style: [
          {
            selector: "node",
            style: {
              width: "data(size)",
              height: "data(size)",
              "background-color": "#121118",
              "border-width": 2.5,
              "border-color": "data(color)",
              label: "data(label)",
              color: "#F3F0E8",
              "font-family": "JetBrains Mono, monospace",
              "font-size": "9px",
              "text-valign": "bottom",
              "text-margin-y": 4,
              "min-zoomed-font-size": 7,
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-color": "#FFFFFF",
              "border-width": 4,
              "background-color": "#22202A",
            },
          },
          {
            selector: "edge",
            style: {
              width: "data(weight)",
              "line-color": "#2A2834",
              "target-arrow-color": "#524E65",
              "target-arrow-shape": showArrows ? "triangle" : "none",
              "curve-style": "bezier",
              "arrow-scale": 0.85,
              opacity: 0.8,
            },
          },
          {
            selector: "edge[?isCross]",
            style: {
              "line-color": "#E5B95C",
              "line-style": "dashed",
              opacity: 0.85,
            },
          },
          {
            selector: ".neighbor-highlight",
            style: {
              "border-color": "#00E575",
              "border-width": 3,
            },
          },
          {
            selector: ".dimmed",
            style: {
              opacity: 0.15,
            },
          },
        ],
        layout: {
          name: "cose",
          idealEdgeLength: 70,
          nodeOverlap: 24,
          refresh: 20,
          fit: true,
          padding: 30,
          randomize: false,
          componentSpacing: 80,
          nodeRepulsion: 450000,
          edgeElasticity: 100,
        } as any,
        userZoomingEnabled: true,
        userPanningEnabled: true,
      });

      // Node Click Handler (Clarification 7: Highlight 1-hop neighbors, dim others)
      cy.on("tap", "node", (evt: any) => {
        const node = evt.target;
        const nodeItem = node.data("nodeData") as NetworkNodeItem;
        setSelectedNode(nodeItem);
        setSelectedEdge(null);

        // Highlight neighborhood
        cy.elements().removeClass("neighbor-highlight dimmed");
        const neighborhood = node.neighborhood().add(node);
        cy.elements().difference(neighborhood).addClass("dimmed");
        neighborhood.nodes().difference(node).addClass("neighbor-highlight");
      });

      // Edge Click Handler
      cy.on("tap", "edge", (evt: any) => {
        const edge = evt.target;
        const edgeItem = edge.data("edgeData") as NetworkEdgeItem;
        setSelectedEdge(edgeItem);
        setSelectedNode(null);
      });

      // Canvas background click clears selection
      cy.on("tap", (evt: any) => {
        if (evt.target === cy) {
          setSelectedNode(null);
          setSelectedEdge(null);
          cy.elements().removeClass("neighbor-highlight dimmed");
        }
      });

      cyRef.current = cy;
    }

    renderGraph();

    return () => {
      isMounted = false;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [filteredNodes, filteredEdges, showLabels, showArrows]);

  return (
    <section id="network" className="scroll-mt-24 py-6 border-t border-[#1C1A20] font-mono">
      {/* Header */}
      <div className="mb-4 flex items-baseline justify-between flex-wrap gap-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="size-1.5 rounded-full bg-intel-gold" />
            <p className="text-[11px] font-semibold tracking-[0.16em] uppercase text-intel-goldLight">
              Network Topology Workstation
            </p>
          </div>
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-intel-text font-sans">
            Directed Interaction Multigraph & Community Structure
          </h2>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {onOpenEvidence && (
            <button
              onClick={() => onOpenEvidence("pagerank")}
              className="text-intel-muted hover:text-intel-gold transition-colors cursor-pointer"
            >
              [ PAGERANK & DISTANCE FORMULAS ]
            </button>
          )}
        </div>
      </div>

      {/* Non-Silent Fallback Banner (Correction 8) */}
      {selectedTopicLabel && !hasTopicNetwork && (
        <div className="mb-3 p-3 rounded-lg border border-intel-gold/40 bg-intel-gold/10 text-intel-goldLight flex items-center justify-between flex-wrap gap-2 text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle size={15} className="text-intel-gold shrink-0" />
            <span>
              No topic-specific network analysis available for <strong>#{selectedTopicLabel}</strong>.
            </span>
          </div>
          <span className="text-[10px] uppercase font-bold bg-card-dark px-2 py-0.5 rounded border border-card-border text-intel-muted">
            GLOBAL NETWORK — NOT FILTERED TO SELECTED TOPIC
          </span>
        </div>
      )}

      {/* Main Workstation Container */}
      <div className="border border-card-border bg-[#0B0A0F] rounded-xl overflow-hidden shadow-2xl">
        {/* Controls Toolbar */}
        <div className="p-3.5 border-b border-card-border bg-[#100F16] flex flex-col gap-3 text-xs">
          {/* Row 1: Scope, Components, Ego Mode */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3 flex-wrap">
              {/* Scope Switcher */}
              <div className="flex items-center gap-1 bg-[#16151E] p-0.5 rounded border border-card-border">
                <span className="text-[10px] text-intel-muted uppercase px-2">Scope:</span>
                <button
                  onClick={() => setScopeMode("topic")}
                  disabled={!hasTopicNetwork}
                  className={`px-2 py-0.5 rounded text-[11px] cursor-pointer transition-colors ${
                    scopeMode === "topic" && hasTopicNetwork
                      ? "bg-intel-gold text-black font-bold"
                      : "text-intel-muted hover:text-white disabled:opacity-40"
                  }`}
                >
                  Topic Network
                </button>
                <button
                  onClick={() => setScopeMode("global")}
                  className={`px-2 py-0.5 rounded text-[11px] cursor-pointer transition-colors ${
                    scopeMode === "global" || !hasTopicNetwork
                      ? "bg-intel-gold text-black font-bold"
                      : "text-intel-muted hover:text-white"
                  }`}
                >
                  Global Network
                </button>
              </div>

              {/* Component Filter */}
              <div className="flex items-center gap-1 bg-[#16151E] p-0.5 rounded border border-card-border">
                <span className="text-[10px] text-intel-muted uppercase px-2">Components:</span>
                <button
                  onClick={() => setComponentFilter("largest")}
                  className={`px-2 py-0.5 rounded text-[11px] cursor-pointer transition-colors ${
                    componentFilter === "largest" ? "bg-white text-black font-bold" : "text-intel-muted hover:text-white"
                  }`}
                >
                  Largest ({components[0]?.length || 0} nodes)
                </button>
                <button
                  onClick={() => setComponentFilter("top5")}
                  className={`px-2 py-0.5 rounded text-[11px] cursor-pointer transition-colors ${
                    componentFilter === "top5" ? "bg-white text-black font-bold" : "text-intel-muted hover:text-white"
                  }`}
                >
                  Top 5 Components
                </button>
                <button
                  onClick={() => setComponentFilter("all")}
                  className={`px-2 py-0.5 rounded text-[11px] cursor-pointer transition-colors ${
                    componentFilter === "all" ? "bg-white text-black font-bold" : "text-intel-muted hover:text-white"
                  }`}
                >
                  All Components
                </button>
              </div>
            </div>

            {/* Ego Network Mode Reset */}
            {egoCenterUserId !== null && (
              <div className="flex items-center gap-2 bg-intel-green/10 border border-intel-green/40 px-3 py-1 rounded text-intel-green">
                <span className="text-xs font-bold">EGO NETWORK ACTIVE</span>
                <button
                  onClick={() => setEgoCenterUserId(null)}
                  className="text-[11px] underline hover:text-white cursor-pointer font-bold"
                >
                  BACK TO FULL NETWORK
                </button>
              </div>
            )}
          </div>

          {/* Row 2: Visual Toggles & Sliders */}
          <div className="flex items-center justify-between flex-wrap gap-4 pt-2 border-t border-card-border/60">
            {/* Toggles */}
            <div className="flex items-center gap-3 text-[11px] flex-wrap">
              <label className="flex items-center gap-1.5 cursor-pointer select-none text-intel-muted hover:text-white">
                <input
                  type="checkbox"
                  checked={showIsolated}
                  onChange={(e) => setShowIsolated(e.target.checked)}
                  className="rounded bg-card-dark border-card-border text-intel-gold focus:ring-0"
                />
                <span>Isolated Nodes</span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer select-none text-intel-muted hover:text-white">
                <input
                  type="checkbox"
                  checked={showSelfLoops}
                  onChange={(e) => setShowSelfLoops(e.target.checked)}
                  className="rounded bg-card-dark border-card-border text-intel-gold focus:ring-0"
                />
                <span>Self-Loops</span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer select-none text-intel-muted hover:text-white">
                <input
                  type="checkbox"
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                  className="rounded bg-card-dark border-card-border text-intel-gold focus:ring-0"
                />
                <span>Labels</span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer select-none text-intel-muted hover:text-white">
                <input
                  type="checkbox"
                  checked={showArrows}
                  onChange={(e) => setShowArrows(e.target.checked)}
                  className="rounded bg-card-dark border-card-border text-intel-gold focus:ring-0"
                />
                <span>Directed Arrows</span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer select-none text-intel-goldLight hover:text-white">
                <input
                  type="checkbox"
                  checked={showCrossCommunity}
                  onChange={(e) => setShowCrossCommunity(e.target.checked)}
                  className="rounded bg-card-dark border-card-border text-intel-gold focus:ring-0"
                />
                <span>Cross-Community Edges</span>
              </label>
            </div>

            {/* Sliders: Edge Weight & Observed Interaction Evolution */}
            <div className="flex items-center gap-4 flex-wrap text-xs">
              {/* Edge Weight Slider */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-intel-muted uppercase">Min Weight:</span>
                <input
                  type="range"
                  min="1.0"
                  max={Math.max(maxWeightInDataset, 5.0)}
                  step="0.5"
                  value={minWeight}
                  onChange={(e) => setMinWeight(parseFloat(e.target.value))}
                  className="w-20 accent-intel-gold cursor-pointer"
                />
                <span className="text-[11px] font-bold text-intel-text w-6">{minWeight.toFixed(1)}</span>
              </div>

              {/* Temporal Slider: Observed Interaction Evolution (Correction 11) */}
              {minTimestamp !== maxTimestamp && (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-intel-muted uppercase">Evolution:</span>
                  <input
                    type="range"
                    min="10"
                    max="100"
                    step="5"
                    value={timeProgress}
                    onChange={(e) => setTimeProgress(parseInt(e.target.value))}
                    className="w-24 accent-intel-green cursor-pointer"
                    title="Filter edges by observed interaction timestamp"
                  />
                  <span className="text-[10px] text-intel-green font-bold">
                    {timeProgress === 100 ? "ALL TIME" : `${timeProgress}% SPAN`}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Workstation Canvas & Side Inspector Layout */}
        <div className="relative grid grid-cols-1 lg:grid-cols-[1fr_360px] min-h-[640px]">
          {/* Cytoscape Graph Canvas */}
          <div className="relative w-full h-[640px] bg-[#0A090E] overflow-hidden">
            <div ref={containerRef} className="w-full h-full" />

            {/* Canvas Overlay Controls & Legend */}
            <div className="absolute top-3 left-3 flex flex-col gap-2 pointer-events-none">
              <div className="bg-[#0E0D14]/90 border border-card-border px-3 py-1.5 rounded backdrop-blur text-[10px] text-intel-muted">
                Rendering: <strong className="text-white">{filteredNodes.length} nodes</strong> ·{" "}
                <strong className="text-white">{filteredEdges.length} edges</strong>
              </div>

              {/* Community Color Legend */}
              <div className="bg-[#0E0D14]/90 border border-card-border p-2 rounded backdrop-blur text-[9px] flex flex-col gap-1 max-w-[200px]">
                <span className="font-bold text-intel-muted uppercase">LOUVAIN COMMUNITIES:</span>
                <div className="flex flex-wrap gap-1">
                  {rawNodes.slice(0, 8).map((n) => (
                    <span
                      key={n.user_id}
                      className="px-1.5 py-0.5 rounded text-[8px] font-bold text-black"
                      style={{ background: getCategoricalCommunityColor(n.community_id) }}
                    >
                      Comm {n.community_id ?? "None"}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Sparsity & Transparency Notice (Clarification 10) */}
            <div className="absolute bottom-3 left-3 right-3 lg:right-auto bg-[#0E0D14]/90 border border-card-border px-3 py-1.5 rounded backdrop-blur text-[10px] text-intel-muted flex items-center gap-2">
              <span className="text-intel-gold font-bold uppercase">Sparsity Notice:</span>
              <span>Observed network is highly fragmented in the current sample (density {rawSummary.density.toFixed(4)}).</span>
            </div>
          </div>

          {/* Side Inspector Drawer */}
          <div className="border-t lg:border-t-0 lg:border-l border-card-border bg-[#0E0D14] p-4 md:p-5 flex flex-col justify-between overflow-y-auto">
            {selectedNode ? (
              <div className="flex flex-col gap-4">
                {/* Node Title & Identity */}
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-card-border mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="size-3 rounded-full"
                        style={{ background: getCategoricalCommunityColor(selectedNode.community_id) }}
                      />
                      <span className="text-sm font-bold text-white">@{selectedNode.username}</span>
                    </div>
                    <span
                      className="text-[10px] px-2 py-0.5 rounded font-bold"
                      style={{
                        background: `${getCategoricalCommunityColor(selectedNode.community_id)}20`,
                        color: getCategoricalCommunityColor(selectedNode.community_id),
                        border: `1px solid ${getCategoricalCommunityColor(selectedNode.community_id)}40`,
                      }}
                    >
                      Community {selectedNode.community_id ?? "None"}
                    </span>
                  </div>
                  <span className="text-[10px] text-intel-muted">Internal User ID: {selectedNode.user_id}</span>
                </div>

                {/* Centrality & Rank Context (Clarification 8) */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded bg-card-dark border border-card-border">
                    <span className="text-[9px] uppercase text-intel-muted block">PageRank</span>
                    <span className="text-sm font-bold text-intel-green mt-0.5 block">
                      {selectedNode.pagerank_score.toFixed(6)}
                    </span>
                    <span className="text-[9px] text-intel-muted mt-0.5 block">
                      Rank #{nodeRankContext?.prRank} of {nodeRankContext?.totalCount}
                    </span>
                  </div>

                  <div className="p-2.5 rounded bg-card-dark border border-card-border">
                    <span className="text-[9px] uppercase text-intel-muted block">Betweenness</span>
                    <span className="text-sm font-bold text-intel-gold mt-0.5 block">
                      {selectedNode.betweenness_centrality.toFixed(6)}
                    </span>
                    <span className="text-[9px] text-intel-muted mt-0.5 block">
                      Bridge Rank #{nodeRankContext?.bwRank}
                    </span>
                  </div>

                  <div className="p-2.5 rounded bg-card-dark border border-card-border">
                    <span className="text-[9px] uppercase text-intel-muted block">In / Out Degree</span>
                    <span className="text-xs font-bold text-white mt-0.5 block">
                      In: {selectedNode.in_degree} · Out: {selectedNode.out_degree}
                    </span>
                    <span className="text-[9px] text-intel-muted mt-0.5 block">
                      In-Vol: {selectedNode.weighted_in_degree.toFixed(1)}
                    </span>
                  </div>

                  <div className="p-2.5 rounded bg-card-dark border border-card-border">
                    <span className="text-[9px] uppercase text-intel-muted block">Bridge Reach</span>
                    <span className="text-xs font-bold text-intel-sky mt-0.5 block">
                      {selectedNode.communities_reached} communities
                    </span>
                    <span className="text-[9px] text-intel-muted mt-0.5 block">
                      {selectedNode.cross_community_edge_count} foreign edges
                    </span>
                  </div>
                </div>

                {/* Derived Interaction Totals */}
                <div className="p-3 rounded bg-card-dark border border-card-border text-xs">
                  <span className="text-[10px] uppercase font-bold text-intel-muted block mb-2">
                    OBSERVED ENGAGEMENT TOTALS:
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <span>Replies: <strong className="text-white">{nodeRankContext?.totalReplies}</strong></span>
                    <span>Mentions: <strong className="text-white">{nodeRankContext?.totalMentions}</strong></span>
                    <span>Reposts: <strong className="text-white">{nodeRankContext?.totalReposts}</strong></span>
                    <span>Quotes: <strong className="text-white">{nodeRankContext?.totalQuotes}</strong></span>
                  </div>
                </div>

                {/* Inspector Actions: Ego Network & Related Tweets */}
                <div className="flex flex-col gap-2 pt-2 border-t border-card-border">
                  <button
                    onClick={() => setEgoCenterUserId(selectedNode.user_id)}
                    className="w-full py-1.5 px-3 rounded bg-intel-gold/10 border border-intel-gold/40 text-intel-gold text-xs font-bold hover:bg-intel-gold hover:text-black transition-colors cursor-pointer text-center"
                  >
                    SHOW 1-HOP EGO NETWORK
                  </button>

                  <button
                    onClick={() => handleLoadUserTweets(selectedNode.user_id)}
                    className="w-full py-1.5 px-3 rounded bg-card-elevated border border-card-border text-intel-text text-xs font-bold hover:border-white transition-colors cursor-pointer text-center"
                  >
                    RELATED TWEETS FOR @{selectedNode.username}
                  </button>
                </div>
              </div>
            ) : selectedEdge ? (
              /* Edge Inspector */
              <div className="flex flex-col gap-3">
                <div className="pb-2 border-b border-card-border">
                  <span className="text-[10px] uppercase font-bold text-intel-gold block">
                    INTERACTION EDGE INSPECTION
                  </span>
                  <div className="flex items-center gap-2 mt-1 text-xs font-bold text-white">
                    <span>@{selectedEdge.source_username}</span>
                    <ArrowRight size={12} className="text-intel-muted" />
                    <span>@{selectedEdge.target_username}</span>
                  </div>
                </div>

                <div className="p-3 rounded bg-card-dark border border-card-border text-xs flex flex-col gap-2">
                  <div className="flex justify-between">
                    <span className="text-intel-muted">Aggregated Weight:</span>
                    <strong className="text-intel-green">{selectedEdge.total_weight.toFixed(1)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-intel-muted">Replies:</span>
                    <strong className="text-white">{selectedEdge.reply_count}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-intel-muted">Mentions:</span>
                    <strong className="text-white">{selectedEdge.mention_count}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-intel-muted">Reposts:</span>
                    <strong className="text-white">{selectedEdge.repost_count}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-intel-muted">Quotes:</span>
                    <strong className="text-white">{selectedEdge.quote_count}</strong>
                  </div>
                </div>

                <div className="p-2.5 rounded bg-card-dark border border-card-border text-[10px] text-intel-muted">
                  <span className="block mb-1">
                    First Observed:{" "}
                    <strong className="text-white">
                      {selectedEdge.first_observed_at ? new Date(selectedEdge.first_observed_at).toISOString() : "Unknown"}
                    </strong>
                  </span>
                  <span>
                    Last Observed:{" "}
                    <strong className="text-white">
                      {selectedEdge.last_observed_at ? new Date(selectedEdge.last_observed_at).toISOString() : "Unknown"}
                    </strong>
                  </span>
                </div>
              </div>
            ) : (
              /* Default Empty State */
              <div className="h-full flex flex-col items-center justify-center text-center text-intel-muted p-4 gap-3">
                <Network size={28} className="text-intel-muted/50" />
                <p className="text-xs">
                  Click any node or edge in the topology to inspect uncollapsed centrality metrics, ego networks, and observation timestamps.
                </p>
              </div>
            )}

            {/* Bottom Graph Summary Bar */}
            <div className="pt-3 border-t border-card-border mt-4 text-[10px] text-intel-muted flex justify-between">
              <span>Weak Components: {rawSummary.weak_component_count}</span>
              <span>Largest: {rawSummary.largest_weak_component_size} users</span>
            </div>
          </div>
        </div>
      </div>

      {/* Related Tweets Modal for Inspected Node */}
      {showUserTweetsModal && selectedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in font-mono">
          <div className="w-full max-w-2xl bg-[#0E0D14] border border-card-border rounded-xl p-5 shadow-2xl flex flex-col max-h-[80vh]">
            <div className="flex items-center justify-between pb-3 border-b border-card-border mb-3">
              <div>
                <h3 className="text-sm font-bold text-white">
                  RELATED POSTS BY @{selectedNode.username}
                </h3>
                <p className="text-[10px] text-intel-muted">Internal User ID: {selectedNode.user_id}</p>
              </div>
              <button
                onClick={() => setShowUserTweetsModal(false)}
                className="p-1 rounded hover:bg-card-elevated text-intel-muted hover:text-white transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Tweet List Container */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {isLoadingUserTweets ? (
                <div className="py-12 text-center text-xs text-intel-muted">
                  Loading posts authored by @{selectedNode.username}...
                </div>
              ) : userTweets.length > 0 ? (
                userTweets.map((tw) => (
                  <div
                    key={tw.tweet_id}
                    className="p-3 rounded-lg border border-card-border bg-[#131219] flex flex-col gap-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[10px] text-intel-muted">
                        {new Date(tw.created_at_utc).toLocaleString("en-US", { timeZone: "UTC" })} UTC
                      </span>
                      <span className="text-[9px] px-1.5 py-0.2 rounded border uppercase font-bold text-intel-green border-intel-green/40">
                        {tw.sentiment?.final_sentiment || "NEUTRAL"}
                      </span>
                    </div>
                    <p className="text-xs text-intel-text leading-relaxed font-sans">{tw.text}</p>
                    <div className="flex items-center gap-3 text-[10px] text-intel-muted pt-1 border-t border-card-border/50">
                      <span>Likes: {tw.like_count}</span>
                      <span>Retweets: {tw.retweet_count}</span>
                      <span>Replies: {tw.reply_count}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-xs text-intel-muted">
                  No authored posts found in current sample for @{selectedNode.username}.
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-card-border mt-3 flex justify-end">
              <button
                onClick={() => setShowUserTweetsModal(false)}
                className="px-3 py-1 rounded bg-card-elevated hover:bg-card-border text-white text-xs transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
