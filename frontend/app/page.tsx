"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { AnalysisContextBar } from "@/components/context/AnalysisContextBar";
import { TrendsSection } from "@/components/trends/TrendsSection";
import { NarrativeBrief } from "@/components/narrative/NarrativeBrief";
import { SentimentSection } from "@/components/sentiment/SentimentSection";
import { AudienceSection } from "@/components/audience/AudienceSection";
import { NetworkSection } from "@/components/network/NetworkSection";
import { EvidenceDrawer } from "@/components/common/EvidenceDrawer";
import { GuidedTourModal } from "@/components/workspace/GuidedTourModal";
import { ErrorState, LoadingState } from "@/components/common/FeedbackStates";
import {
  fetchNetworkEdges,
  fetchNetworkNodes,
  fetchNetworkSummary,
  fetchOverview,
  fetchSentimentSummary,
  fetchSentimentTimeline,
  fetchTopicNetwork,
  fetchTopicSentiment,
  fetchTrendDetail,
  fetchTrends,
  fetchTweets,
} from "@/lib/api/client";
import {
  NetworkEdgeItem,
  NetworkNodeItem,
  NetworkSummaryResponse,
  OverviewResponse,
  SentimentSummaryResponse,
  SentimentTimelineResponse,
  TopicNetworkResponse,
  TopicSentimentResponse,
  TrendDetailResponse,
  TrendListResponse,
  TweetItem,
} from "@/lib/types/api";

export default function WorkstationPage() {
  // Global Analytics State
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [trendsList, setTrendsList] = useState<TrendListResponse | null>(null);
  const [sentimentSummary, setSentimentSummary] = useState<SentimentSummaryResponse | null>(null);
  const [sentimentTimeline, setSentimentTimeline] = useState<SentimentTimelineResponse | null>(null);
  const [globalNetSummary, setGlobalNetSummary] = useState<NetworkSummaryResponse | null>(null);
  const [globalNodes, setGlobalNodes] = useState<NetworkNodeItem[]>([]);
  const [globalEdges, setGlobalEdges] = useState<NetworkEdgeItem[]>([]);

  // Selected Topic Investigation State
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [topicDetail, setTopicDetail] = useState<TrendDetailResponse | null>(null);
  const [topicSentiment, setTopicSentiment] = useState<TopicSentimentResponse | null>(null);
  const [topicNetwork, setTopicNetwork] = useState<TopicNetworkResponse | null>(null);
  const [representativeTweets, setRepresentativeTweets] = useState<TweetItem[]>([]);
  const [isLoadingTopicData, setIsLoadingTopicData] = useState(false);

  // Workstation View Mode
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<"narrative" | "network">("narrative");

  // Evidence & Tour Drawers
  const [evidenceMetric, setEvidenceMetric] = useState<string | null>(null);
  const [isTourOpen, setIsTourOpen] = useState(false);

  // Controls & Loading
  const [timelineInterval, setTimelineInterval] = useState("4h");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Initial Data Fetch
  const loadInitialData = useCallback(async () => {
    try {
      setError(null);
      const [ov, tr, ss, st, gNet, gNodes, gEdges] = await Promise.all([
        fetchOverview(),
        fetchTrends(null, 30),
        fetchSentimentSummary(),
        fetchSentimentTimeline(null, timelineInterval),
        fetchNetworkSummary(),
        fetchNetworkNodes({ limit: 120 }),
        fetchNetworkEdges(null, 180),
      ]);

      setOverview(ov);
      setTrendsList(tr);
      setSentimentSummary(ss);
      setSentimentTimeline(st);
      setGlobalNetSummary(gNet);
      setGlobalNodes(gNodes);
      setGlobalEdges(gEdges);

      // Default selected topic to top emerging topic
      const defaultTopicId =
        ov.top_emerging_topic?.topic_id || (tr.topics.length > 0 ? tr.topics[0].topic_id : null);
      if (defaultTopicId && !selectedTopicId) {
        setSelectedTopicId(defaultTopicId);
      }
    } catch (err: any) {
      console.error("Workstation initial fetch error:", err);
      setError(err.message || "Failed to connect to backend analytics.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [timelineInterval, selectedTopicId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Topic Selection Effect
  useEffect(() => {
    if (!selectedTopicId) return;

    let isMounted = true;
    setIsLoadingTopicData(true);

    async function loadTopicData(tid: number) {
      try {
        const [det, sent, net, tw] = await Promise.all([
          fetchTrendDetail(tid),
          fetchTopicSentiment(tid),
          fetchTopicNetwork(tid),
          fetchTweets({ topic_id: tid, page_size: 9 }),
        ]);

        if (isMounted) {
          setTopicDetail(det);
          setTopicSentiment(sent);
          setTopicNetwork(net);
          setRepresentativeTweets(tw.items);
        }
      } catch (err) {
        console.error(`Failed to fetch details for topic ${tid}:`, err);
      } finally {
        if (isMounted) {
          setIsLoadingTopicData(false);
        }
      }
    }

    loadTopicData(selectedTopicId);

    return () => {
      isMounted = false;
    };
  }, [selectedTopicId]);

  // Timeline interval handler
  const handleIntervalChange = async (interval: string) => {
    setTimelineInterval(interval);
    try {
      const st = await fetchSentimentTimeline(selectedTopicId, interval);
      setSentimentTimeline(st);
    } catch (err) {
      console.error("Failed to update sentiment timeline:", err);
    }
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    loadInitialData();
  };

  // INVESTIGATE button handler
  const handleInvestigateTopic = (topicId: number) => {
    setSelectedTopicId(topicId);
    // Scroll smoothly to narrative progression
    const el = document.getElementById("progression");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#070709] flex items-center justify-center">
        <LoadingState message="Connecting to PostgreSQL Read API..." />
      </div>
    );
  }

  if (error || !overview || !trendsList || !sentimentSummary || !sentimentTimeline || !globalNetSummary) {
    return (
      <div className="min-h-screen bg-[#070709] flex items-center justify-center p-4">
        <ErrorState
          title="Backend Read Layer Unavailable"
          message={error || "Could not retrieve analytical data from FastAPI endpoints."}
          onRetry={loadInitialData}
        />
      </div>
    );
  }

  const selectedTopicLabel = topicDetail?.label || trendsList.topics.find((t) => t.topic_id === selectedTopicId)?.label;

  return (
    <div className="min-h-screen flex flex-col bg-[#070709] text-intel-text selection:bg-intel-gold selection:text-black font-mono">
      {/* 1. Header with UTC Timestamp */}
      <Header
        lastUpdated={overview.generated_at}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* 2. Persistent Analysis Context Bar (Clarification 2 & 3) */}
      <AnalysisContextBar
        overview={overview}
        selectedTopicDetail={topicDetail}
        onLaunchTour={() => setIsTourOpen(true)}
        onOpenEvidence={(type) => setEvidenceMetric(type)}
      />

      {/* 3. Workstation Navigation Tabs */}
      <div className="border-b border-card-border bg-[#08070C] px-4 md:px-8 lg:px-10">
        <div className="max-w-[1680px] mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-1 text-xs">
            <button
              onClick={() => setActiveWorkspaceTab("narrative")}
              className={`py-3 px-4 border-b-2 font-bold transition-all cursor-pointer ${
                activeWorkspaceTab === "narrative"
                  ? "border-intel-gold text-intel-gold bg-intel-gold/5"
                  : "border-transparent text-intel-muted hover:text-white"
              }`}
            >
              1. NARRATIVE SIGNALS & INVESTIGATION
            </button>
            <button
              onClick={() => setActiveWorkspaceTab("network")}
              className={`py-3 px-4 border-b-2 font-bold transition-all cursor-pointer ${
                activeWorkspaceTab === "network"
                  ? "border-intel-gold text-intel-gold bg-intel-gold/5"
                  : "border-transparent text-intel-muted hover:text-white"
              }`}
            >
              2. INTERACTION TOPOLOGY WORKSTATION
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-[11px] text-intel-muted">
            <span>Discovered Narratives: <strong className="text-white">{trendsList.topics.length}</strong></span>
            <span>·</span>
            <span>Network Density: <strong className="text-intel-sky">{globalNetSummary.density.toFixed(5)}</strong></span>
          </div>
        </div>
      </div>

      {/* 4. Main Workstation Body */}
      <main className="flex-1 max-w-[1680px] w-full mx-auto px-4 md:px-8 lg:px-10 py-6">
        {activeWorkspaceTab === "narrative" ? (
          <div className="flex flex-col gap-6">
            {/* 1. Emerging Narratives Roster with INVESTIGATE -> */}
            <TrendsSection
              topics={trendsList.topics}
              selectedTopicId={selectedTopicId}
              onInvestigateTopic={handleInvestigateTopic}
            />

            {/* 2. Observed Narrative Progression for selectedTopicId */}
            <NarrativeBrief
              topicDetail={topicDetail}
              topicSentiment={topicSentiment}
              topicNetwork={topicNetwork}
              representativeTweets={representativeTweets}
              isLoadingTweets={isLoadingTopicData}
              onOpenEvidence={(type) => setEvidenceMetric(type)}
            />

            {/* 3. Sentiment Velocity & Sarcasm Fusion Stacked Timeline */}
            <SentimentSection
              summary={sentimentSummary}
              timeline={sentimentTimeline}
              selectedTopicLabel={selectedTopicLabel}
              onIntervalChange={handleIntervalChange}
              currentInterval={timelineInterval}
              onOpenEvidence={(type) => setEvidenceMetric(type)}
            />

            {/* 4. Compact Demographics Unavailable Banner (Clarification 16) */}
            <AudienceSection />
          </div>
        ) : (
          /* 5. Interaction Topology Workstation (Cytoscape.js) */
          <div>
            <NetworkSection
              globalSummary={globalNetSummary}
              globalNodes={globalNodes}
              globalEdges={globalEdges}
              topicNetwork={topicNetwork}
              selectedTopicLabel={selectedTopicLabel}
              onOpenEvidence={(type) => setEvidenceMetric(type)}
            />
          </div>
        )}
      </main>

      {/* Slide-Over Evidence & Calculation Provenance Drawer */}
      <EvidenceDrawer
        isOpen={evidenceMetric !== null}
        onClose={() => setEvidenceMetric(null)}
        metricType={evidenceMetric || "overview"}
        contextData={{
          topicLabel: selectedTopicLabel || undefined,
          velocity: topicDetail?.velocity,
          baseline: topicDetail?.baseline_mentions,
          mentions: topicDetail?.current_mentions,
          trendRunId: topicDetail?.run_id || 3,
          networkRunId: globalNetSummary?.run_id || 2,
        }}
      />

      {/* Guided Tour Modal (Lightweight Jury/Demo Workflow) */}
      <GuidedTourModal
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        topicDetail={topicDetail}
        topicSentiment={topicSentiment}
        topicNetwork={topicNetwork}
      />

      {/* Footer */}
      <Footer />
    </div>
  );
}
