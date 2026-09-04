"use client";

import React, { useState } from "react";
import { X, ChevronRight, ChevronLeft, Sparkles, TrendingUp, Compass, MessageSquare, Network, ShieldCheck } from "lucide-react";
import { TopicNetworkResponse, TopicSentimentResponse, TrendDetailResponse } from "@/lib/types/api";

interface GuidedTourModalProps {
  isOpen: boolean;
  onClose: () => void;
  topicDetail: TrendDetailResponse | null;
  topicSentiment: TopicSentimentResponse | null;
  topicNetwork: TopicNetworkResponse | null;
  onSelectTopicSection?: (sectionId: string) => void;
}

export function GuidedTourModal({
  isOpen,
  onClose,
  topicDetail,
  topicSentiment,
  topicNetwork,
  onSelectTopicSection,
}: GuidedTourModalProps) {
  const [currentStep, setCurrentStep] = useState(1);

  if (!isOpen || !topicDetail) return null;

  const topPr = topicNetwork?.top_pagerank_nodes?.[0];
  const topBridge = topicNetwork?.top_bridge_nodes?.[0];

  const totalSent = (topicSentiment?.positive ?? 0) + (topicSentiment?.neutral ?? 0) + (topicSentiment?.negative ?? 0);
  const posPct = totalSent > 0 ? Math.round(((topicSentiment?.positive ?? 0) / totalSent) * 100) : 0;
  const negPct = totalSent > 0 ? Math.round(((topicSentiment?.negative ?? 0) / totalSent) * 100) : 0;

  const steps = [
    {
      step: 1,
      title: "Step 1: Detected Emerging Narrative",
      icon: <Compass size={18} className="text-intel-gold" />,
      content: (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-intel-muted">
            The pipeline automatically discovered narrative cluster <strong>#{topicDetail.label}</strong> using MiniLM sentence embeddings and HDBSCAN density clustering.
          </p>
          <div className="p-3 rounded-lg border border-card-border bg-card-dark flex flex-col gap-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-intel-muted">Cluster Type:</span>
              <span className="font-bold text-intel-gold uppercase">{topicDetail.topic_type}</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-intel-muted">Assigned Tweets:</span>
              <span className="font-bold text-white">{topicDetail.tweet_count}</span>
            </div>
            <div>
              <span className="text-[10px] text-intel-muted block mb-1">REPRESENTATIVE TERMS:</span>
              <div className="flex flex-wrap gap-1">
                {topicDetail.representative_terms.map((t) => (
                  <span key={t} className="px-2 py-0.5 rounded text-[10px] bg-card-elevated border border-card-border text-intel-text">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 2,
      title: "Step 2: Temporal Emergence & Velocity",
      icon: <TrendingUp size={18} className="text-intel-green" />,
      content: (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-intel-muted">
            Mentions are aggregated into 15-minute chronological windows and evaluated against a rolling 2-hour baseline.
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 rounded bg-card-dark border border-card-border">
              <span className="text-[10px] text-intel-muted block uppercase">Current Mentions</span>
              <span className="text-sm font-bold text-white mt-0.5 block">{topicDetail.current_mentions}</span>
            </div>
            <div className="p-2.5 rounded bg-card-dark border border-card-border">
              <span className="text-[10px] text-intel-muted block uppercase">Baseline (2h)</span>
              <span className="text-sm font-bold text-intel-muted mt-0.5 block">{topicDetail.baseline_mentions}</span>
            </div>
            <div className="p-2.5 rounded bg-card-dark border border-card-border">
              <span className="text-[10px] text-intel-muted block uppercase">Velocity Multiplier</span>
              <span className="text-sm font-bold text-intel-green mt-0.5 block">{topicDetail.velocity.toFixed(2)}×</span>
            </div>
            <div className="p-2.5 rounded bg-card-dark border border-card-border">
              <span className="text-[10px] text-intel-muted block uppercase">Acceleration</span>
              <span className="text-sm font-bold text-intel-text mt-0.5 block">
                {topicDetail.acceleration >= 0 ? `+${topicDetail.acceleration}` : topicDetail.acceleration}
              </span>
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 3,
      title: "Step 3: Sentiment & Sarcasm Fusion",
      icon: <MessageSquare size={18} className="text-intel-sky" />,
      content: (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-intel-muted">
            Tweets undergo joint inference with CardiffNLP XLM-RoBERTa sentiment classification and T5 sarcasm generation log-probabilities.
          </p>
          <div className="p-3 rounded-lg border border-card-border bg-card-dark flex flex-col gap-2 text-xs">
            <div className="flex justify-between">
              <span className="text-intel-muted">Discourse Tone:</span>
              <span className="font-bold text-white">{posPct}% Positive · {negPct}% Negative</span>
            </div>
            <div className="flex justify-between">
              <span className="text-intel-muted">High Sarcasm Evidence:</span>
              <span className="font-bold text-intel-gold">{topicSentiment?.high_sarcasm_evidence ?? 0} tweets (score ≥ 0.85)</span>
            </div>
            <div className="pt-2 border-t border-card-border/60 text-[10px] text-intel-muted">
              Fusion decisions are strictly deterministic decision tree rules preserving uncalibrated log-likelihood semantics.
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 4,
      title: "Step 4: Influential & Bridge Accounts",
      icon: <ShieldCheck size={18} className="text-intel-purple" />,
      content: (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-intel-muted">
            Directed interaction paths identify central amplifiers and accounts bridging disparate Louvain discourse communities.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 rounded bg-card-dark border border-card-border">
              <span className="text-[10px] uppercase font-bold text-intel-green block">Top Influencer (PageRank)</span>
              <span className="text-xs font-bold text-white mt-1 block">@{topPr ? topPr.username : "None in topic"}</span>
              <span className="text-[10px] text-intel-muted mt-0.5 block">
                PR: {topPr ? topPr.pagerank_score.toFixed(6) : "N/A"}
              </span>
            </div>
            <div className="p-2.5 rounded bg-card-dark border border-card-border">
              <span className="text-[10px] uppercase font-bold text-intel-gold block">Top Bridge (Betweenness)</span>
              <span className="text-xs font-bold text-white mt-1 block">@{topBridge ? topBridge.username : "None in topic"}</span>
              <span className="text-[10px] text-intel-muted mt-0.5 block">
                BW: {topBridge ? topBridge.betweenness_centrality.toFixed(6) : "N/A"}
              </span>
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 5,
      title: "Step 5: Interaction Topology & Ego View",
      icon: <Network size={18} className="text-intel-goldLight" />,
      content: (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-intel-muted">
            Explore the real directed interaction multigraph in the Network Workstation. Filter to the largest connected component, inspect 1-hop ego networks, and trace observed interaction evolution over time.
          </p>
          <div className="p-3 rounded-lg border border-intel-gold/40 bg-intel-gold/10 text-intel-goldLight text-xs">
            Switch to the <strong>Interaction Topology Workstation</strong> tab above to interact with the full Cytoscape.js canvas!
          </div>
        </div>
      ),
    },
  ];

  const activeStepData = steps[currentStep - 1];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in font-mono">
      <div className="w-full max-w-xl bg-[#0D0C11] border border-card-border rounded-xl p-6 shadow-2xl flex flex-col justify-between">
        <div>
          {/* Modal Header */}
          <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded bg-intel-gold/10 flex items-center justify-center text-intel-gold">
                {activeStepData.icon}
              </div>
              <h3 className="text-sm font-bold text-white">{activeStepData.title}</h3>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-card-elevated text-intel-muted hover:text-white transition-colors cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>

          {/* Stepper Dots */}
          <div className="flex items-center gap-1.5 mb-5">
            {steps.map((s) => (
              <div
                key={s.step}
                onClick={() => setCurrentStep(s.step)}
                className={`h-1.5 flex-1 rounded-full cursor-pointer transition-all ${
                  s.step === currentStep ? "bg-intel-gold" : s.step < currentStep ? "bg-intel-green" : "bg-card-border"
                }`}
              />
            ))}
          </div>

          {/* Step Content */}
          <div className="min-h-[170px]">{activeStepData.content}</div>
        </div>

        {/* Modal Controls */}
        <div className="flex items-center justify-between pt-4 border-t border-card-border mt-6 text-xs">
          <button
            onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
            disabled={currentStep === 1}
            className={`flex items-center gap-1 px-3 py-1.5 rounded transition-colors ${
              currentStep === 1 ? "text-intel-muted/40 cursor-not-allowed" : "hover:bg-card-elevated text-intel-text cursor-pointer"
            }`}
          >
            <ChevronLeft size={14} /> Back
          </button>

          <span className="text-[11px] text-intel-muted font-semibold">
            {currentStep} of {steps.length}
          </span>

          {currentStep < steps.length ? (
            <button
              onClick={() => setCurrentStep((prev) => Math.min(steps.length, prev + 1))}
              className="flex items-center gap-1 px-3 py-1.5 rounded bg-intel-gold text-black font-bold hover:bg-intel-goldLight transition-colors cursor-pointer"
            >
              Next <ChevronRight size={14} />
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded bg-intel-green text-black font-bold hover:bg-white transition-colors cursor-pointer"
            >
              Finish Tour
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
