import React from "react";
import { MessageSquare, TrendingUp, Compass, Network } from "lucide-react";
import { OverviewResponse } from "@/lib/types/api";

interface KeySignalsProps {
  overview: OverviewResponse;
}

export function KeySignals({ overview }: KeySignalsProps) {
  const { dataset, analysis_coverage, sentiment, top_emerging_topic, network } = overview;

  return (
    <section id="overview" className="scroll-mt-24 py-8 border-t border-[#1C1A20] first:border-t-0 first:pt-4">
      <div className="mb-4 flex items-baseline justify-between flex-wrap gap-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="size-1.5 rounded-full bg-intel-gold" />
            <p className="text-[11px] font-semibold tracking-[0.16em] uppercase text-intel-goldLight font-mono">
              Overview
            </p>
          </div>
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-intel-text">
            Key Analytical Signals
          </h2>
        </div>
        <p className="text-xs text-intel-muted font-mono">
          Twitter / X Aggregates · Persisted PostgreSQL Telemetry
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Posts Analyzed */}
        <div className="rounded-xl border border-card-border bg-card p-4 md:p-5 flex flex-col justify-between relative overflow-hidden group hover:border-[#383344] transition-all">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-intel-muted">Posts Analyzed</p>
            <div className="size-7 rounded-md flex items-center justify-center bg-intel-gold/10 text-intel-goldLight">
              <MessageSquare size={15} />
            </div>
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight font-mono text-intel-text">
              {dataset.total_tweets.toLocaleString()}
            </p>
            <div className="flex items-center gap-1.5 mt-1 text-[11px] font-mono">
              <span className="text-intel-green font-semibold bg-intel-green/10 px-1.5 py-0.5 rounded">
                {analysis_coverage.sentiment_analyzed} analyzed
              </span>
              <span className="text-intel-muted">across {dataset.total_users} users</span>
            </div>
          </div>
        </div>

        {/* KPI 2: Positive Sentiment */}
        <div className="rounded-xl border border-card-border bg-card p-4 md:p-5 flex flex-col justify-between relative overflow-hidden group hover:border-[#383344] transition-all">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-intel-muted">Positive Sentiment</p>
            <div className="size-7 rounded-md flex items-center justify-center bg-intel-green/10 text-intel-green">
              <TrendingUp size={15} />
            </div>
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight font-mono text-intel-text">
              {sentiment.positive_percentage}%
            </p>
            <div className="flex items-center gap-1.5 mt-1 text-[11px] font-mono">
              <span className="text-intel-muted">
                Neg: <strong className="text-intel-red">{sentiment.negative_percentage}%</strong>
              </span>
              <span className="text-intel-muted">· Neu: {sentiment.neutral_percentage}%</span>
            </div>
          </div>
        </div>

        {/* KPI 3: Primary Breakout Topic */}
        <div className="rounded-xl border border-card-border bg-card p-4 md:p-5 flex flex-col justify-between relative overflow-hidden group hover:border-[#383344] transition-all">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-intel-muted">Top Velocity Topic</p>
            <div className="size-7 rounded-md flex items-center justify-center bg-intel-gold/10 text-intel-gold">
              <Compass size={15} />
            </div>
          </div>
          <div>
            <p className="text-xl font-bold tracking-tight font-mono text-intel-goldLight truncate" title={top_emerging_topic?.label || "None"}>
              {top_emerging_topic?.label ? `#${top_emerging_topic.label.split(" / ")[0]}` : "No topic"}
            </p>
            <div className="flex items-center gap-1.5 mt-1 text-[11px] font-mono">
              {top_emerging_topic ? (
                <>
                  <span className="text-intel-green font-semibold bg-intel-green/10 px-1.5 py-0.5 rounded">
                    {top_emerging_topic.velocity.toFixed(1)}× velocity
                  </span>
                  <span className="text-intel-muted">+{top_emerging_topic.mention_count} mentions</span>
                </>
              ) : (
                <span className="text-intel-muted">Pending trend run</span>
              )}
            </div>
          </div>
        </div>

        {/* KPI 4: Network Interaction Topology */}
        <div className="rounded-xl border border-card-border bg-card p-4 md:p-5 flex flex-col justify-between relative overflow-hidden group hover:border-[#383344] transition-all">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-intel-muted">Network Topology</p>
            <div className="size-7 rounded-md flex items-center justify-center bg-intel-sky/10 text-intel-sky">
              <Network size={15} />
            </div>
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight font-mono text-intel-text">
              {network.connected_users} <span className="text-sm font-normal text-intel-muted">users</span>
            </p>
            <div className="flex items-center gap-1.5 mt-1 text-[11px] font-mono">
              <span className="text-intel-sky font-semibold bg-intel-sky/10 px-1.5 py-0.5 rounded">
                {network.edges} edges
              </span>
              <span className="text-intel-muted">in {network.communities} communities</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
