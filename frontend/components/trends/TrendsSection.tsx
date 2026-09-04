"use client";

import React, { useState } from "react";
import { Search, ChevronRight, Compass, ArrowUpRight } from "lucide-react";
import { TrendItem } from "@/lib/types/api";

interface TrendsSectionProps {
  topics: TrendItem[];
  selectedTopicId: number | null;
  onInvestigateTopic: (topicId: number) => void;
}

export function TrendsSection({
  topics,
  selectedTopicId,
  onInvestigateTopic,
}: TrendsSectionProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  const filteredTopics = topics.filter((t) => {
    const matchesSearch =
      !searchQuery ||
      t.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.representative_terms.some((term) => term.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesType = !typeFilter || t.topic_type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <section id="narratives" className="scroll-mt-24 py-6 border-t border-[#1C1A20] font-mono">
      {/* Section Header */}
      <div className="mb-4 flex items-baseline justify-between flex-wrap gap-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="size-1.5 rounded-full bg-intel-gold" />
            <p className="text-[11px] font-semibold tracking-[0.16em] uppercase text-intel-goldLight">
              Emerging Narratives
            </p>
          </div>
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-intel-text font-sans">
            Discovered Narrative Clusters & Velocity Signals
          </h2>
        </div>
        <p className="text-xs text-intel-muted">
          Click Investigate to pin narrative context across all analytical panels
        </p>
      </div>

      {/* Filter / Search Bar */}
      <div className="p-3 border border-card-border bg-[#0E0D13] rounded-t-xl flex items-center justify-between gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-intel-muted" />
          <input
            type="text"
            placeholder="Filter by narrative or term..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#16151C] border border-card-border rounded-md pl-9 pr-3 py-1.5 text-xs text-intel-text placeholder:text-intel-muted/50 focus:outline-none focus:border-intel-gold"
          />
        </div>

        <div className="flex items-center gap-1.5 text-xs">
          <button
            onClick={() => setTypeFilter(null)}
            className={`px-2.5 py-1 rounded text-[11px] cursor-pointer transition-colors ${
              typeFilter === null
                ? "bg-intel-gold text-black font-bold"
                : "bg-card-dark border border-card-border text-intel-muted hover:text-white"
            }`}
          >
            All Types
          </button>
          <button
            onClick={() => setTypeFilter("semantic")}
            className={`px-2.5 py-1 rounded text-[11px] cursor-pointer transition-colors ${
              typeFilter === "semantic"
                ? "bg-intel-gold text-black font-bold"
                : "bg-card-dark border border-card-border text-intel-muted hover:text-white"
            }`}
          >
            Semantic
          </button>
          <button
            onClick={() => setTypeFilter("lexical")}
            className={`px-2.5 py-1 rounded text-[11px] cursor-pointer transition-colors ${
              typeFilter === "lexical"
                ? "bg-intel-gold text-black font-bold"
                : "bg-card-dark border border-card-border text-intel-muted hover:text-white"
            }`}
          >
            Lexical
          </button>
        </div>
      </div>

      {/* Table Header */}
      <div className="hidden lg:grid grid-cols-[40px_1.5fr_100px_90px_110px_90px_110px] gap-3 px-4 py-2.5 text-[10px] uppercase font-bold tracking-wider text-intel-muted border-x border-b border-card-border bg-[#0A090E]">
        <span>#</span>
        <span>Narrative & Representative Terms</span>
        <span>Scope</span>
        <span className="text-right">Tweets</span>
        <span className="text-right">Mentions (Cur/Base)</span>
        <span className="text-right">Velocity</span>
        <span className="text-center">Action</span>
      </div>

      {/* Narrative Rows */}
      <div className="border-x border-b border-card-border divide-y divide-card-border rounded-b-xl overflow-hidden bg-[#0A090E]">
        {filteredTopics.length > 0 ? (
          filteredTopics.map((topic, idx) => {
            const isSelected = selectedTopicId === topic.topic_id;

            return (
              <div
                key={topic.topic_id}
                className={`transition-colors px-4 py-3 flex flex-col lg:grid lg:grid-cols-[40px_1.5fr_100px_90px_110px_90px_110px] gap-2 lg:gap-3 items-start lg:items-center ${
                  isSelected ? "bg-[#181622] border-l-2 border-l-intel-gold" : "hover:bg-[#111016]"
                }`}
              >
                {/* Rank */}
                <span className="text-xs font-bold text-intel-muted">#{idx + 1}</span>

                {/* Narrative Label & Representative Terms (Clarification 5: neutral label) */}
                <div className="min-w-0 pr-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold truncate ${isSelected ? "text-intel-gold" : "text-white"}`}>
                      #{topic.label}
                    </span>
                    {isSelected && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-intel-gold/20 text-intel-gold font-bold">
                        ACTIVE WORKSPACE
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 mt-1 overflow-hidden">
                    <span className="text-[9px] text-intel-muted uppercase shrink-0">TERMS:</span>
                    <span className="text-[10px] text-intel-muted truncate">
                      {topic.representative_terms.slice(0, 5).join(", ") || "General vocabulary"}
                    </span>
                  </div>
                </div>

                {/* Scope */}
                <div>
                  <span className="text-[10px] px-2 py-0.5 rounded border border-card-border bg-card-dark text-intel-muted uppercase">
                    {topic.topic_type}
                  </span>
                </div>

                {/* Tweets Assigned */}
                <div className="text-right">
                  <span className="text-xs font-bold text-white">{topic.tweet_count}</span>
                  <span className="text-[10px] text-intel-muted block">posts</span>
                </div>

                {/* Mentions (Current / Baseline) */}
                <div className="text-right">
                  <span className="text-xs font-bold text-intel-text">{topic.current_mentions}</span>
                  <span className="text-[10px] text-intel-muted block">base: {topic.baseline_mentions}</span>
                </div>

                {/* Velocity */}
                <div className="text-right">
                  <span className={`text-xs font-bold ${topic.velocity > 1.5 ? "text-intel-green" : "text-intel-text"}`}>
                    {topic.velocity.toFixed(2)}×
                  </span>
                  <span className="text-[10px] text-intel-muted block">
                    acc: {topic.acceleration >= 0 ? `+${topic.acceleration}` : topic.acceleration}
                  </span>
                </div>

                {/* INVESTIGATE Action */}
                <div className="flex justify-end lg:justify-center w-full lg:w-auto">
                  <button
                    onClick={() => onInvestigateTopic(topic.topic_id)}
                    className={`flex items-center gap-1 px-3 py-1 rounded text-xs font-bold transition-all cursor-pointer ${
                      isSelected
                        ? "bg-intel-gold text-black shadow-[0_0_8px_rgba(229,185,92,0.3)]"
                        : "border border-intel-gold/40 text-intel-gold hover:bg-intel-gold hover:text-black"
                    }`}
                  >
                    INVESTIGATE <ArrowUpRight size={12} />
                  </button>
                </div>
              </div>
            );
          })
        ) : (
          <div className="py-12 text-center text-xs text-intel-muted">
            No narrative clusters match the search criteria.
          </div>
        )}
      </div>
    </section>
  );
}
