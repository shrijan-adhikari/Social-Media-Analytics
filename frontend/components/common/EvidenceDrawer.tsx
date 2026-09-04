"use client";

import React from "react";
import { X, ShieldCheck, Database, Cpu, HelpCircle } from "lucide-react";

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  metricType: "velocity" | "pagerank" | "sentiment" | "betweenness" | "overview" | string;
  contextData?: {
    topicLabel?: string;
    velocity?: number;
    baseline?: number;
    mentions?: number;
    trendRunId?: number;
    networkRunId?: number;
    pagerank?: number;
    betweenness?: number;
    username?: string;
  };
}

export function EvidenceDrawer({
  isOpen,
  onClose,
  metricType,
  contextData,
}: EvidenceDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm animate-fade-in font-mono">
      <div className="w-full max-w-lg bg-[#0E0D13] border-l border-card-border p-6 flex flex-col justify-between overflow-y-auto shadow-2xl">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-card-border mb-6">
            <div className="flex items-center gap-2.5">
              <ShieldCheck size={18} className="text-intel-gold" />
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-intel-text">
                  EVIDENCE & HOW IT WAS CALCULATED
                </h3>
                <p className="text-[10px] text-intel-muted">
                  Deterministic Model & Mathematical Provenance
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-card-elevated text-intel-muted hover:text-white transition-colors cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body Content according to metricType */}
          <div className="flex flex-col gap-6 text-xs text-intel-text leading-relaxed">
            {/* Database & Ingestion Layer Provenance */}
            <div className="p-3.5 rounded-lg border border-card-border bg-[#141318]">
              <div className="flex items-center gap-2 mb-2 text-intel-goldLight font-bold text-[11px]">
                <Database size={14} />
                <span>CANONICAL PERSISTENCE PROVENANCE</span>
              </div>
              <p className="text-[11px] text-intel-muted">
                All metrics are read directly from PostgreSQL 17 using versioned analysis run identifiers. The dashboard read layer executes zero heavy ML inference during HTTP requests.
              </p>
            </div>

            {/* Velocity Evidence */}
            {(metricType === "velocity" || metricType === "overview") && (
              <div className="p-4 rounded-lg border border-card-border bg-card-dark flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-intel-green">
                    1. Mention Velocity & Acceleration
                  </span>
                  <span className="text-[10px] text-intel-muted">Phase 3A Pipeline</span>
                </div>

                <div className="p-2.5 rounded bg-[#09080C] border border-card-border text-[11px] text-intel-text">
                  <code>velocity = current_mentions / max(baseline_mentions, 1.0)</code>
                </div>

                <ul className="list-disc list-inside text-[11px] text-intel-muted space-y-1">
                  <li><strong>Window Duration:</strong> 15 minutes rolling step.</li>
                  <li><strong>Baseline Span:</strong> 8 preceding 15m windows (2-hour rolling baseline).</li>
                  <li><strong>Smoothing / Minimum Support:</strong> Requires at least 2 mentions; topics with fewer than 2 mentions receive velocity = 0.0 to prevent 0 to 1 spurious spikes.</li>
                  <li><strong>Embedding Model:</strong> <code>sentence-transformers/all-MiniLM-L6-v2</code></li>
                  <li><strong>Clustering Algorithm:</strong> HDBSCAN (min_cluster_size = 3, metric = cosine).</li>
                  {contextData?.trendRunId && <li><strong>Trend Analysis Run ID:</strong> #{contextData.trendRunId}</li>}
                </ul>
              </div>
            )}

            {/* PageRank & Network Centrality Evidence */}
            {(metricType === "pagerank" || metricType === "betweenness" || metricType === "overview") && (
              <div className="p-4 rounded-lg border border-card-border bg-card-dark flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-intel-sky">
                    2. Weighted PageRank & Shortest-Path Betweenness
                  </span>
                  <span className="text-[10px] text-intel-muted">Phase 4 Engine</span>
                </div>

                <div className="p-2.5 rounded bg-[#09080C] border border-card-border text-[11px] text-intel-text">
                  <code>Betweenness Distance: distance = 1.0 / total_weight</code>
                </div>

                <ul className="list-disc list-inside text-[11px] text-intel-muted space-y-1">
                  <li><strong>Graph Structure:</strong> Directed multigraph aggregated into pairwise interaction weights A to B (actor to referenced user).</li>
                  <li><strong>PageRank Semantics:</strong> Calculated on incoming directed edges with damping factor alpha = 0.85, max iterations = 100, tolerance = 1e-6.</li>
                  <li><strong>Weighted Betweenness Semantics:</strong> Derives distance as 1.0 / weight so that higher interaction strength translates to shorter graph distance without modifying canonical edge weight.</li>
                  <li><strong>Louvain Communities:</strong> Computed on the explicit undirected weighted projection W(A,B) = W(A to B) + W(B to A) with fixed seed = 42.</li>
                  {contextData?.networkRunId && <li><strong>Network Analysis Run ID:</strong> #{contextData.networkRunId}</li>}
                </ul>
              </div>
            )}

            {/* Sentiment & Sarcasm Fusion Evidence */}
            {(metricType === "sentiment" || metricType === "overview") && (
              <div className="p-4 rounded-lg border border-card-border bg-card-dark flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-intel-gold">
                    3. Sentiment Classification & Sarcasm Fusion
                  </span>
                  <span className="text-[10px] text-intel-muted">Phase 2 Pipeline</span>
                </div>

                <ul className="list-disc list-inside text-[11px] text-intel-muted space-y-1">
                  <li><strong>Primary Sentiment Model:</strong> <code>cardiffnlp/twitter-xlm-roberta-base-sentiment</code></li>
                  <li><strong>Sarcasm Model:</strong> <code>mrm8488/t5-base-finetuned-sarcasm-twitter</code></li>
                  <li><strong>Sarcasm Score Semantics:</strong> Represents the uncalibrated T5 sequence log-likelihood proxy score (0.0 to 1.0), NOT a calibrated softmax probability.</li>
                  <li><strong>High Sarcasm Evidence Threshold:</strong> Sarcasm proxy score &ge; 0.85.</li>
                  <li><strong>Fusion Outcomes:</strong> Deterministic decision tree outputting strictly <code>NO_SARCASM</code>, <code>SARCASM_CONSISTENT</code>, <code>SARCASM_AMBIGUOUS</code>, or <code>SARCASM_UNCERTAIN</code>.</li>
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-card-border mt-6 flex items-center justify-between text-[11px] text-intel-muted">
          <span>Social Media Analytics · SIH26152</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-card-elevated hover:bg-card-border text-intel-text transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
