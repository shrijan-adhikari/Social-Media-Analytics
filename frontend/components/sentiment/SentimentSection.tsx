"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { HelpCircle, BarChart3, Percent } from "lucide-react";
import { SentimentSummaryResponse, SentimentTimelineResponse } from "@/lib/types/api";

interface SentimentSectionProps {
  summary: SentimentSummaryResponse;
  timeline: SentimentTimelineResponse;
  selectedTopicLabel?: string | null;
  onIntervalChange?: (interval: string) => void;
  currentInterval?: string;
  onOpenEvidence?: (metricType: string) => void;
}

export function SentimentSection({
  summary,
  timeline,
  selectedTopicLabel,
  onIntervalChange,
  currentInterval = "4h",
  onOpenEvidence,
}: SentimentSectionProps) {
  const { positive, neutral, negative, sarcasm, total_analyzed } = summary;
  const [chartMode, setChartMode] = useState<"percentage" | "volume">("percentage");

  // Custom Exact Tooltip (Clarification 13: exact counts in tooltip)
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const pt = payload[0]?.payload;
    if (!pt) return null;

    return (
      <div className="rounded-lg border border-card-borderLight bg-[#131218] px-3.5 py-2.5 text-xs shadow-2xl font-mono">
        <p className="mb-2 text-[10px] uppercase font-bold text-intel-goldLight">
          WINDOW: {label}
        </p>
        <div className="flex flex-col gap-1">
          <div className="flex justify-between gap-4 text-intel-green">
            <span>Positive:</span>
            <strong>{pt.positive} ({pt.positive_pct}%)</strong>
          </div>
          <div className="flex justify-between gap-4 text-intel-muted">
            <span>Neutral:</span>
            <strong>{pt.neutral} ({pt.neutral_pct}%)</strong>
          </div>
          <div className="flex justify-between gap-4 text-intel-red">
            <span>Negative:</span>
            <strong>{pt.negative} ({pt.negative_pct}%)</strong>
          </div>
          <div className="pt-1.5 mt-1 border-t border-card-border flex justify-between gap-4 text-white font-bold">
            <span>Total Evaluated:</span>
            <span>{pt.total}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <section id="sentiment" className="scroll-mt-24 py-6 border-t border-[#1C1A20] font-mono">
      {/* Section Header */}
      <div className="mb-4 flex items-baseline justify-between flex-wrap gap-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="size-1.5 rounded-full bg-intel-gold" />
            <p className="text-[11px] font-semibold tracking-[0.16em] uppercase text-intel-goldLight">
              Sentiment Velocity & Sarcasm Fusion
            </p>
          </div>
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-intel-text font-sans">
            Discourse Tone Dynamics
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {onOpenEvidence && (
            <button
              onClick={() => onOpenEvidence("sentiment")}
              className="text-[11px] text-intel-muted hover:text-intel-gold transition-colors flex items-center gap-1 cursor-pointer"
            >
              [ HOW CALCULATED ? ]
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4">
        {/* Left: Stacked Timeline (Volume vs Percentage Toggle) */}
        <div className="border border-card-border bg-[#0B0A0F] rounded-xl p-4 md:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-card-border mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white">Sentiment Trajectory</span>
                <span className="text-[10px] text-intel-muted">
                  {selectedTopicLabel ? `(#${selectedTopicLabel})` : "(All Topics)"}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs">
                {/* Mode Toggle (Clarification 13) */}
                <div className="flex items-center bg-[#15141B] border border-card-border rounded p-0.5 text-[10px]">
                  <button
                    onClick={() => setChartMode("percentage")}
                    className={`px-2 py-0.5 rounded cursor-pointer transition-colors ${
                      chartMode === "percentage" ? "bg-intel-gold text-black font-bold" : "text-intel-muted hover:text-white"
                    }`}
                  >
                    Percentage
                  </button>
                  <button
                    onClick={() => setChartMode("volume")}
                    className={`px-2 py-0.5 rounded cursor-pointer transition-colors ${
                      chartMode === "volume" ? "bg-intel-gold text-black font-bold" : "text-intel-muted hover:text-white"
                    }`}
                  >
                    Volume
                  </button>
                </div>

                {/* Interval Selector */}
                {onIntervalChange && (
                  <div className="flex items-center bg-[#15141B] border border-card-border rounded p-0.5 text-[10px]">
                    {["1h", "4h", "1d"].map((int) => (
                      <button
                        key={int}
                        onClick={() => onIntervalChange(int)}
                        className={`px-1.5 py-0.5 rounded cursor-pointer transition-colors ${
                          currentInterval === int ? "bg-white text-black font-bold" : "text-intel-muted hover:text-white"
                        }`}
                      >
                        {int}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Area Chart */}
            <div className="h-56 w-full pt-1">
              {timeline.points.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline.points} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="2 3" stroke="#1C1A22" vertical={false} />
                    <XAxis
                      dataKey="timestamp"
                      tick={{ fontSize: 10, fill: "#85817B", fontFamily: "JetBrains Mono" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      domain={chartMode === "percentage" ? [0, 100] : ["auto", "auto"]}
                      tick={{ fontSize: 10, fill: "#85817B", fontFamily: "JetBrains Mono" }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v) => (chartMode === "percentage" ? `${v}%` : v.toString())}
                      width={38}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey={chartMode === "percentage" ? "positive_pct" : "positive"}
                      name="Positive"
                      stroke="#00E575"
                      fill="#00E575"
                      fillOpacity={0.18}
                      strokeWidth={2}
                    />
                    <Area
                      type="monotone"
                      dataKey={chartMode === "percentage" ? "neutral_pct" : "neutral"}
                      name="Neutral"
                      stroke="#8E97AC"
                      fill="#8E97AC"
                      fillOpacity={0.12}
                      strokeWidth={1.5}
                    />
                    <Area
                      type="monotone"
                      dataKey={chartMode === "percentage" ? "negative_pct" : "negative"}
                      name="Negative"
                      stroke="#FF3B5C"
                      fill="#FF3B5C"
                      fillOpacity={0.2}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-intel-muted">
                  No time-bucketed points in current window
                </div>
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-card-border mt-3 text-[11px] text-intel-muted flex justify-between items-center">
            <span>Overall Dataset Sample: {total_analyzed} posts</span>
            <div className="flex items-center gap-3">
              <span className="text-intel-green font-bold">Pos: {positive.percentage}%</span>
              <span className="text-intel-muted">Neu: {neutral.percentage}%</span>
              <span className="text-intel-red font-bold">Neg: {negative.percentage}%</span>
            </div>
          </div>
        </div>

        {/* Right: Sarcasm & Deterministic Fusion States */}
        <div className="border border-card-border bg-[#0B0A0F] rounded-xl p-4 md:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-card-border mb-3">
              <span className="text-xs font-bold text-white">Sarcasm & Fusion Telemetry</span>
              <span className="text-[10px] text-intel-gold font-bold">T5 Finetuned</span>
            </div>

            {/* Sarcasm KPI Box */}
            <div className="grid grid-cols-2 gap-2 text-xs mb-3">
              <div className="p-2.5 rounded bg-[#121118] border border-card-border">
                <span className="text-[9px] uppercase text-intel-muted block">High Evidence</span>
                <span className="text-sm font-bold text-intel-gold mt-0.5 block">
                  {sarcasm.high_evidence_count} tweets
                </span>
                <span className="text-[9px] text-intel-muted mt-0.5 block">score ≥ 0.85 threshold</span>
              </div>

              <div className="p-2.5 rounded bg-[#121118] border border-card-border">
                <span className="text-[9px] uppercase text-intel-muted block">Avg Proxy Score</span>
                <span className="text-sm font-bold text-intel-text mt-0.5 block">
                  {sarcasm.average_sarcasm_score !== null ? sarcasm.average_sarcasm_score.toFixed(3) : "N/A"}
                </span>
                <span className="text-[9px] text-intel-muted mt-0.5 block">T5 generation log-prob</span>
              </div>
            </div>

            {/* Stored Fusion Outcomes (Clarification 4: exact stored fusion states) */}
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase font-bold text-intel-muted">
                PERSISTED FUSION STATES
              </span>

              <div className="p-2 rounded bg-[#121118] border border-card-border flex justify-between items-center text-xs">
                <span className="text-intel-green font-semibold">NO_SARCASM</span>
                <strong className="text-white">{sarcasm.no_sarcasm_count}</strong>
              </div>
              <div className="p-2 rounded bg-[#121118] border border-card-border flex justify-between items-center text-xs">
                <span className="text-intel-gold font-semibold">SARCASM_CONSISTENT</span>
                <strong className="text-white">{sarcasm.sarcasm_consistent_count}</strong>
              </div>
              <div className="p-2 rounded bg-[#121118] border border-card-border flex justify-between items-center text-xs">
                <span className="text-intel-purple font-semibold">SARCASM_AMBIGUOUS</span>
                <strong className="text-white">{sarcasm.sarcasm_ambiguous_count}</strong>
              </div>
              <div className="p-2 rounded bg-[#121118] border border-card-border flex justify-between items-center text-xs">
                <span className="text-intel-muted font-semibold">SARCASM_UNCERTAIN</span>
                <strong className="text-white">{sarcasm.sarcasm_uncertain_count}</strong>
              </div>
            </div>
          </div>

          <p className="mt-3 pt-2 text-[9px] text-intel-muted border-t border-card-border">
            Sarcasm scores represent uncalibrated token log-likelihoods. Fusion statuses follow deterministic decision tree rules.
          </p>
        </div>
      </div>
    </section>
  );
}
