"use client";

import React from "react";
import { Sparkles, Layers, Clock, Database, Radio } from "lucide-react";
import { OverviewResponse, TrendDetailResponse } from "@/lib/types/api";

interface AnalysisContextBarProps {
  overview: OverviewResponse;
  selectedTopicDetail: TrendDetailResponse | null;
  onLaunchTour?: () => void;
  onOpenEvidence?: (metricType: string) => void;
}

export function AnalysisContextBar({
  overview,
  selectedTopicDetail,
  onLaunchTour,
  onOpenEvidence,
}: AnalysisContextBarProps) {
  const { dataset, top_emerging_topic, network, generated_at } = overview;

  const topicLabel = selectedTopicDetail?.label || top_emerging_topic?.label || "None Selected";

  return (
    <section className="border-b border-card-border bg-[#0B0A0F] text-xs font-mono py-2.5 px-4 md:px-8 lg:px-10">
      <div className="max-w-[1680px] mx-auto flex items-center justify-between gap-4 flex-wrap">
        {/* Left Context Strip */}
        <div className="flex items-center gap-4 flex-wrap">
          {/* Active Narrative */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-intel-muted">
              ACTIVE NARRATIVE:
            </span>
            <span className="text-intel-gold font-bold px-2 py-0.5 rounded bg-intel-gold/10 border border-intel-gold/30 truncate max-w-[280px]">
              #{topicLabel}
            </span>
          </div>

          <span className="text-card-border hidden sm:inline">|</span>

          {/* Trend Window vs Data Range (Clarification 3) */}
          <div className="flex items-center gap-3 text-intel-muted">
            <div className="flex items-center gap-1.5" title="Window duration for velocity & acceleration computation">
              <Clock size={12} className="text-intel-sky" />
              <span>Trend Window: <strong className="text-intel-text">15m</strong></span>
            </div>
            <div className="flex items-center gap-1.5" title="Total chronological span of ingested dataset">
              <Database size={12} className="text-intel-green" />
              <span>Dataset Range: <strong className="text-intel-text">{dataset.total_tweets} tweets</strong></span>
            </div>
          </div>

          <span className="text-card-border hidden md:inline">|</span>

          {/* Model Runs Telemetry */}
          <div className="hidden lg:flex items-center gap-3 text-intel-muted">
            <div className="flex items-center gap-1">
              <Layers size={12} />
              <span>Trend Run: <strong className="text-intel-text">#{selectedTopicDetail?.run_id ?? 3}</strong></span>
            </div>
            <div className="flex items-center gap-1">
              <Radio size={12} />
              <span>Network Run: <strong className="text-intel-text">#{network.latest_run_id ?? 2}</strong></span>
            </div>
          </div>
        </div>

        {/* Right Actions: Evidence / How Calculated & Guided Tour */}
        <div className="flex items-center gap-2.5">
          {onOpenEvidence && (
            <button
              onClick={() => onOpenEvidence("overview")}
              className="text-[11px] text-intel-muted hover:text-intel-gold transition-colors flex items-center gap-1 cursor-pointer"
              title="Inspect methodology and calculation provenance"
            >
              [ EVIDENCE & PROVENANCE ]
            </button>
          )}

          {onLaunchTour && (
            <button
              onClick={onLaunchTour}
              className="flex items-center gap-1.5 px-3 py-1 rounded border border-intel-gold/50 bg-intel-gold/10 text-intel-gold font-bold hover:bg-intel-gold hover:text-black transition-all cursor-pointer shadow-[0_0_10px_rgba(229,185,92,0.15)]"
            >
              <Sparkles size={13} />
              INVESTIGATE TOP SIGNAL
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
