"use client";

import React, { useState } from "react";
import {
  Compass,
  TrendingUp,
  Network,
  ShieldCheck,
  Heart,
  Repeat,
  MessageSquare,
  X,
  Filter,
} from "lucide-react";
import {
  TopicNetworkResponse,
  TopicSentimentResponse,
  TrendDetailResponse,
  TweetItem,
} from "@/lib/types/api";

interface NarrativeBriefProps {
  topicDetail: TrendDetailResponse | null;
  topicSentiment: TopicSentimentResponse | null;
  topicNetwork: TopicNetworkResponse | null;
  representativeTweets: TweetItem[];
  isLoadingTweets?: boolean;
  onOpenEvidence?: (metricType: string) => void;
}

export function NarrativeBrief({
  topicDetail,
  topicSentiment,
  topicNetwork,
  representativeTweets,
  isLoadingTweets,
  onOpenEvidence,
}: NarrativeBriefProps) {
  const [selectedTweet, setSelectedTweet] = useState<TweetItem | null>(null);
  const [sentimentFilter, setSentimentFilter] = useState<string | null>(null);

  if (!topicDetail) {
    return (
      <div className="py-12 text-center text-xs font-mono text-intel-muted border-t border-card-border">
        Select an emerging narrative above to inspect its observed progression.
      </div>
    );
  }

  const { label, velocity, acceleration, current_mentions, baseline_mentions, tweet_count, created_at, representative_terms } = topicDetail;

  const topPr = topicNetwork?.top_pagerank_nodes?.[0];
  const topBridge = topicNetwork?.top_bridge_nodes?.[0];

  const totalPrNodes = topicNetwork?.nodes?.length || 0;
  const totalSent = (topicSentiment?.positive ?? 0) + (topicSentiment?.neutral ?? 0) + (topicSentiment?.negative ?? 0);
  const posPct = totalSent > 0 ? Math.round(((topicSentiment?.positive ?? 0) / totalSent) * 100) : 0;
  const neuPct = totalSent > 0 ? Math.round(((topicSentiment?.neutral ?? 0) / totalSent) * 100) : 0;
  const negPct = totalSent > 0 ? Math.round(((topicSentiment?.negative ?? 0) / totalSent) * 100) : 0;

  // Filter tweets
  const filteredTweets = representativeTweets.filter((tw) => {
    if (!sentimentFilter) return true;
    if (sentimentFilter === "sarcasm") return tw.sentiment?.high_sarcasm_evidence;
    return tw.sentiment?.final_sentiment?.toLowerCase() === sentimentFilter;
  });

  return (
    <section id="progression" className="scroll-mt-24 py-6 border-t border-[#1C1A20] font-mono">
      {/* Section Header */}
      <div className="mb-4 flex items-baseline justify-between flex-wrap gap-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="size-1.5 rounded-full bg-intel-gold" />
            <p className="text-[11px] font-semibold tracking-[0.16em] uppercase text-intel-goldLight">
              Narrative Intelligence Workstation
            </p>
          </div>
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-intel-text font-sans">
            Observed Narrative Progression: #{label}
          </h2>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {onOpenEvidence && (
            <button
              onClick={() => onOpenEvidence("velocity")}
              className="text-intel-muted hover:text-intel-gold transition-colors cursor-pointer"
            >
              [ EVIDENCE & FORMULAS ]
            </button>
          )}
        </div>
      </div>

      {/* Main Progression Telemetry Container */}
      <div className="border border-card-border bg-[#0B0A0F] rounded-xl overflow-hidden shadow-2xl">
        {/* Top Telemetry Strip */}
        <div className="p-4 md:p-5 border-b border-card-border bg-[#100F15] flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span className="text-lg font-bold text-intel-goldLight">#{label}</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-intel-green/10 border border-intel-green/40 text-intel-green font-bold">
                VELOCITY {velocity.toFixed(2)}×
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-card-dark border border-card-border text-intel-muted">
                ACCEL {acceleration >= 0 ? `+${acceleration}` : acceleration}
              </span>
            </div>

            {/* Clarification 4: FIRST OBSERVED IN SAMPLE */}
            <div className="text-[11px] text-intel-muted">
              <span>FIRST OBSERVED IN SAMPLE: </span>
              <strong className="text-white">
                {new Date(created_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  timeZone: "UTC",
                })} UTC
              </strong>
            </div>
          </div>

          {/* Unified Progression Telemetry Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            {/* Mention Volume */}
            <div className="p-3 rounded-lg border border-card-border bg-[#14131A]">
              <span className="text-[10px] uppercase text-intel-muted block">WINDOW MENTIONS</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-base font-bold text-white">{current_mentions}</span>
                <span className="text-[10px] text-intel-muted">vs baseline {baseline_mentions}</span>
              </div>
              <span className="text-[9px] text-intel-green mt-1 block">
                {tweet_count} total assigned posts
              </span>
            </div>

            {/* Sentiment Breakdown */}
            <div className="p-3 rounded-lg border border-card-border bg-[#14131A]">
              <span className="text-[10px] uppercase text-intel-muted block">SENTIMENT RATIO</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-xs font-bold text-intel-green">{posPct}% Pos</span>
                <span className="text-xs font-bold text-intel-muted">{neuPct}% Neu</span>
                <span className="text-xs font-bold text-intel-red">{negPct}% Neg</span>
              </div>
              <span className="text-[9px] text-intel-gold mt-1 block">
                {topicSentiment?.high_sarcasm_evidence ?? 0} high-sarcasm instances
              </span>
            </div>

            {/* Top Influencer with Rank context (Clarification 8) */}
            <div className="p-3 rounded-lg border border-card-border bg-[#14131A]">
              <span className="text-[10px] uppercase text-intel-muted block">TOP AMPLIFIER</span>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-xs font-bold text-white truncate">
                  @{topPr ? topPr.username : "None in topic"}
                </span>
                <span className="text-[10px] text-intel-green font-bold">
                  {topPr ? `PR ${topPr.pagerank_score.toFixed(4)}` : ""}
                </span>
              </div>
              <span className="text-[9px] text-intel-muted mt-1 block">
                {topPr ? `Rank #1 of ${totalPrNodes} in topic` : "No topic network"}
              </span>
            </div>

            {/* Top Bridge with Rank context (Clarification 8) */}
            <div className="p-3 rounded-lg border border-card-border bg-[#14131A]">
              <span className="text-[10px] uppercase text-intel-muted block">TOP BRIDGE ACCOUNT</span>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-xs font-bold text-white truncate">
                  @{topBridge ? topBridge.username : "None in topic"}
                </span>
                <span className="text-[10px] text-intel-gold font-bold">
                  {topBridge ? `BW ${topBridge.betweenness_centrality.toFixed(4)}` : ""}
                </span>
              </div>
              <span className="text-[9px] text-intel-muted mt-1 block">
                {topBridge ? `Crosses ${topBridge.communities_reached} foreign communities` : "Direct ties"}
              </span>
            </div>
          </div>

          {/* Representative Terms (Clarification 5) */}
          <div className="flex items-center gap-2 flex-wrap text-xs pt-1">
            <span className="text-[10px] uppercase font-bold text-intel-muted shrink-0">
              REPRESENTATIVE TERMS:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {representative_terms.map((term) => (
                <span
                  key={term}
                  className="px-2 py-0.5 rounded text-[11px] border border-card-border bg-[#16151E] text-intel-text"
                >
                  {term}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Representative Tweets Stream with Sentiment Filter Pills */}
        <div className="p-4 md:p-5 bg-[#0A090E]">
          <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                REPRESENTATIVE TWEETS // #{label}
              </h3>
              <p className="text-[10px] text-intel-muted">
                Click any post to inspect sentiment, sarcasm log-likelihood, and engagement
              </p>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1.5 text-xs">
              <button
                onClick={() => setSentimentFilter(null)}
                className={`px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors ${
                  sentimentFilter === null ? "bg-white text-black font-bold" : "bg-card-dark text-intel-muted hover:text-white"
                }`}
              >
                All ({representativeTweets.length})
              </button>
              <button
                onClick={() => setSentimentFilter("positive")}
                className={`px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors ${
                  sentimentFilter === "positive" ? "bg-intel-green text-black font-bold" : "bg-card-dark text-intel-green hover:bg-intel-green/10"
                }`}
              >
                Positive
              </button>
              <button
                onClick={() => setSentimentFilter("negative")}
                className={`px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors ${
                  sentimentFilter === "negative" ? "bg-intel-red text-black font-bold" : "bg-card-dark text-intel-red hover:bg-intel-red/10"
                }`}
              >
                Negative
              </button>
              <button
                onClick={() => setSentimentFilter("sarcasm")}
                className={`px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors ${
                  sentimentFilter === "sarcasm" ? "bg-intel-gold text-black font-bold" : "bg-card-dark text-intel-gold hover:bg-intel-gold/10"
                }`}
              >
                High Sarcasm
              </button>
            </div>
          </div>

          {isLoadingTweets ? (
            <div className="py-8 text-center text-xs text-intel-muted">
              Loading representative posts...
            </div>
          ) : filteredTweets.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredTweets.map((tweet) => {
                const s = tweet.sentiment?.final_sentiment?.toLowerCase() || "neutral";
                const badgeColor =
                  s === "positive"
                    ? "bg-intel-green/10 text-intel-green border-intel-green/30"
                    : s === "negative"
                    ? "bg-intel-red/10 text-intel-red border-intel-red/30"
                    : "bg-card-border text-intel-muted border-card-border";

                return (
                  <div
                    key={tweet.tweet_id}
                    onClick={() => setSelectedTweet(tweet)}
                    className="p-3.5 rounded-lg border border-card-border bg-[#111016] hover:border-intel-gold/40 hover:bg-[#14131B] transition-all cursor-pointer flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-white">@{tweet.username}</span>
                        <div className="flex items-center gap-1.5">
                          {tweet.sentiment?.high_sarcasm_evidence && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-intel-gold/10 border border-intel-gold/40 text-intel-gold font-bold">
                              SARCASM
                            </span>
                          )}
                          <span className={`text-[9px] px-1.5 py-0.2 rounded border uppercase font-bold ${badgeColor}`}>
                            {s}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-intel-text leading-relaxed line-clamp-3 font-sans">
                        {tweet.text}
                      </p>
                    </div>

                    <div className="flex items-center justify-between mt-3 pt-2 border-t border-card-border/50 text-[10px] text-intel-muted">
                      <span>
                        {new Date(tweet.created_at_utc).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          timeZone: "UTC",
                        })}
                      </span>
                      <div className="flex items-center gap-2.5">
                        <span className="flex items-center gap-0.5"><Heart size={10} /> {tweet.like_count}</span>
                        <span className="flex items-center gap-0.5"><Repeat size={10} /> {tweet.retweet_count}</span>
                        <span className="flex items-center gap-0.5"><MessageSquare size={10} /> {tweet.reply_count}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-intel-muted">
              No tweets match the selected sentiment filter.
            </div>
          )}
        </div>
      </div>

      {/* Tweet Detailed Inspection Modal */}
      {selectedTweet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-lg bg-[#0E0D14] border border-card-border rounded-xl p-5 shadow-2xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-card-border mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">@{selectedTweet.username}</span>
                  <span className="text-[10px] text-intel-muted">ID: {selectedTweet.tweet_id}</span>
                </div>
                <button
                  onClick={() => setSelectedTweet(null)}
                  className="p-1 rounded hover:bg-card-elevated text-intel-muted hover:text-white transition-colors cursor-pointer"
                >
                  <X size={16} />
                </button>
              </div>

              <p className="text-sm text-intel-text leading-relaxed font-sans mb-4 p-3 rounded-lg bg-[#14131B] border border-card-border">
                {selectedTweet.text}
              </p>

              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                <div className="p-2 rounded bg-card-dark border border-card-border">
                  <span className="text-[10px] text-intel-muted block">FINAL SENTIMENT</span>
                  <span className="text-xs font-bold text-intel-green uppercase mt-0.5 block">
                    {selectedTweet.sentiment?.final_sentiment} (conf: {selectedTweet.sentiment?.final_confidence})
                  </span>
                </div>
                <div className="p-2 rounded bg-card-dark border border-card-border">
                  <span className="text-[10px] text-intel-muted block">SARCASM PROXY</span>
                  <span className="text-xs font-bold text-intel-gold mt-0.5 block">
                    {selectedTweet.sentiment?.sarcasm_score !== null && selectedTweet.sentiment?.sarcasm_score !== undefined
                      ? selectedTweet.sentiment.sarcasm_score.toFixed(4)
                      : "Not Evaluated"}
                  </span>
                </div>
                <div className="p-2 rounded bg-card-dark border border-card-border">
                  <span className="text-[10px] text-intel-muted block">FUSION STATUS</span>
                  <span className="text-xs font-bold text-intel-text mt-0.5 block">
                    {selectedTweet.sentiment?.fusion_status || "NO_SARCASM"}
                  </span>
                </div>
                <div className="p-2 rounded bg-card-dark border border-card-border">
                  <span className="text-[10px] text-intel-muted block">TOPIC ASSIGNMENT</span>
                  <span className="text-xs font-bold text-intel-sky mt-0.5 block truncate">
                    #{selectedTweet.topic?.label || label}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-card-border flex items-center justify-between text-[11px] text-intel-muted">
              <span>Post time: {new Date(selectedTweet.created_at_utc).toISOString()}</span>
              <button
                onClick={() => setSelectedTweet(null)}
                className="px-3 py-1 rounded bg-card-elevated hover:bg-card-border text-white transition-colors cursor-pointer"
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
