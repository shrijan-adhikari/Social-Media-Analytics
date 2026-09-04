/**
 * Typed API Client connecting the Next.js frontend to the FastAPI read API.
 * Uses centralized NEXT_PUBLIC_API_URL.
 */

import {
  CommunityFlowItem,
  CommunityItem,
  NetworkEdgeItem,
  NetworkNodeItem,
  NetworkSummaryResponse,
  OverviewResponse,
  SentimentSummaryResponse,
  SentimentTimelineResponse,
  SystemAnalysisStatusResponse,
  TopicNetworkResponse,
  TopicSentimentResponse,
  TrendDetailResponse,
  TrendListResponse,
  TrendTimelineResponse,
  TweetListResponse,
} from "@/lib/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      cache: "no-store",
    });

    if (!res.ok) {
      const errorBody = await res.text();
      throw new Error(`API Error ${res.status}: ${res.statusText} (${errorBody})`);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`Fetch failed for ${endpoint}:`, err);
    throw err;
  }
}

export async function fetchOverview(): Promise<OverviewResponse> {
  return apiFetch<OverviewResponse>("/api/v1/overview");
}

export async function fetchTweets(params?: {
  page?: number;
  page_size?: number;
  topic_id?: number | null;
  user_id?: number | null;
  username?: string | null;
  sentiment?: string | null;
  fusion_status?: string | null;
}): Promise<TweetListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append("page", params.page.toString());
  if (params?.page_size) query.append("page_size", params.page_size.toString());
  if (params?.topic_id) query.append("topic_id", params.topic_id.toString());
  if (params?.user_id) query.append("user_id", params.user_id.toString());
  if (params?.username) query.append("username", params.username);
  if (params?.sentiment) query.append("sentiment", params.sentiment);
  if (params?.fusion_status) query.append("fusion_status", params.fusion_status);

  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<TweetListResponse>(`/api/v1/tweets${qs}`);
}

export async function fetchSentimentSummary(topicId?: number | null): Promise<SentimentSummaryResponse> {
  const qs = topicId ? `?topic_id=${topicId}` : "";
  return apiFetch<SentimentSummaryResponse>(`/api/v1/sentiment/summary${qs}`);
}

export async function fetchSentimentTimeline(topicId?: number | null, interval = "4h"): Promise<SentimentTimelineResponse> {
  const query = new URLSearchParams({ interval });
  if (topicId) query.append("topic_id", topicId.toString());
  return apiFetch<SentimentTimelineResponse>(`/api/v1/sentiment/timeline?${query.toString()}`);
}

export async function fetchTrends(topicType?: string | null, limit = 20): Promise<TrendListResponse> {
  const query = new URLSearchParams({ limit: limit.toString() });
  if (topicType) query.append("topic_type", topicType);
  return apiFetch<TrendListResponse>(`/api/v1/trends?${query.toString()}`);
}

export async function fetchTrendDetail(topicId: number): Promise<TrendDetailResponse> {
  return apiFetch<TrendDetailResponse>(`/api/v1/trends/${topicId}`);
}

export async function fetchTrendTimeline(topicId: number): Promise<TrendTimelineResponse> {
  return apiFetch<TrendTimelineResponse>(`/api/v1/trends/${topicId}/timeline`);
}

export async function fetchTopicSentiment(topicId: number): Promise<TopicSentimentResponse> {
  return apiFetch<TopicSentimentResponse>(`/api/v1/trends/${topicId}/sentiment`);
}

export async function fetchTopicNetwork(topicId: number): Promise<TopicNetworkResponse> {
  return apiFetch<TopicNetworkResponse>(`/api/v1/trends/${topicId}/network`);
}

export async function fetchNetworkSummary(runId?: number | null): Promise<NetworkSummaryResponse> {
  const qs = runId ? `?run_id=${runId}` : "";
  return apiFetch<NetworkSummaryResponse>(`/api/v1/network/summary${qs}`);
}

export async function fetchNetworkNodes(params?: {
  run_id?: number | null;
  limit?: number;
  community_id?: number | null;
}): Promise<NetworkNodeItem[]> {
  const query = new URLSearchParams();
  if (params?.run_id) query.append("run_id", params.run_id.toString());
  if (params?.limit) query.append("limit", params.limit.toString());
  if (params?.community_id !== undefined && params?.community_id !== null) {
    query.append("community_id", params.community_id.toString());
  }

  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<NetworkNodeItem[]>(`/api/v1/network/nodes${qs}`);
}

export async function fetchNetworkEdges(runId?: number | null, limit = 100): Promise<NetworkEdgeItem[]> {
  const query = new URLSearchParams({ limit: limit.toString() });
  if (runId) query.append("run_id", runId.toString());
  return apiFetch<NetworkEdgeItem[]>(`/api/v1/network/edges?${query.toString()}`);
}

export async function fetchNetworkCommunities(runId?: number | null): Promise<CommunityItem[]> {
  const qs = runId ? `?run_id=${runId}` : "";
  return apiFetch<CommunityItem[]>(`/api/v1/network/communities${qs}`);
}

export async function fetchNetworkFlows(runId?: number | null): Promise<CommunityFlowItem[]> {
  const qs = runId ? `?run_id=${runId}` : "";
  return apiFetch<CommunityFlowItem[]>(`/api/v1/network/flows${qs}`);
}

export async function fetchAnalysisStatus(): Promise<SystemAnalysisStatusResponse> {
  return apiFetch<SystemAnalysisStatusResponse>("/api/v1/analysis/status");
}
