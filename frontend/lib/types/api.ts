/**
 * API Type Definitions for Social Media Analytics
 * Matches FastAPI backend Pydantic models exactly.
 */

export interface DatasetMetrics {
  total_tweets: number;
  total_users: number;
  total_interactions: number;
}

export interface AnalysisCoverage {
  sentiment_analyzed: number;
  sarcasm_analyzed: number;
  topic_assigned: number;
}

export interface SentimentOverview {
  positive_percentage: number;
  neutral_percentage: number;
  negative_percentage: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
}

export interface TopEmergingTopic {
  topic_id: number;
  label: string;
  topic_type: string;
  velocity: number;
  acceleration: number;
  mention_count: number;
}

export interface NetworkOverview {
  latest_run_id: number | null;
  connected_users: number;
  edges: number;
  communities: number;
  density: number;
  weak_component_count: number;
  largest_weak_component_size: number;
  is_sparse: boolean;
}

export interface OverviewResponse {
  generated_at: string;
  pipeline_status: string;
  dataset: DatasetMetrics;
  analysis_coverage: AnalysisCoverage;
  sentiment: SentimentOverview;
  top_emerging_topic: TopEmergingTopic | null;
  network: NetworkOverview;
}

export interface SentimentCount {
  count: number;
  percentage: number;
}

export interface SarcasmBreakdown {
  analyzed: number;
  high_evidence_count: number;
  no_sarcasm_count: number;
  sarcasm_uncertain_count: number;
  sarcasm_consistent_count: number;
  sarcasm_ambiguous_count: number;
  average_sarcasm_score: number | null;
}

export interface SentimentSummaryResponse {
  total_analyzed: number;
  positive: SentimentCount;
  neutral: SentimentCount;
  negative: SentimentCount;
  sarcasm: SarcasmBreakdown;
  pipeline_metadata: Record<string, any>;
}

export interface SentimentTimelinePoint {
  timestamp: string;
  positive: number;
  neutral: number;
  negative: number;
  total: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
}

export interface SentimentTimelineResponse {
  points: SentimentTimelinePoint[];
  interval: string;
  topic_id?: number | null;
}

export interface TrendItem {
  topic_id: number;
  topic_type: string;
  label: string;
  representative_terms: string[];
  tweet_count: number;
  current_mentions: number;
  baseline_mentions: number;
  velocity: number;
  acceleration: number;
  latest_window_start?: string | null;
  latest_window_end?: string | null;
}

export interface TrendListResponse {
  run_id: number;
  pipeline_version: string;
  clustering_algorithm: string;
  topics: TrendItem[];
}

export interface TrendDetailResponse {
  topic_id: number;
  run_id: number;
  label: string;
  topic_type: string;
  representative_terms: string[];
  tweet_count: number;
  current_mentions: number;
  baseline_mentions: number;
  velocity: number;
  acceleration: number;
  created_at: string;
}

export interface TrendTimelinePoint {
  window_start: string;
  window_end: string;
  mention_count: number;
  baseline_mentions: number;
  velocity: number;
  acceleration: number;
  like_count: number;
  repost_count: number;
  reply_count: number;
  quote_count: number;
}

export interface TrendTimelineResponse {
  topic_id: number;
  label: string;
  points: TrendTimelinePoint[];
}

export interface TopicSentimentResponse {
  topic_id: number;
  label: string;
  tweet_count: number;
  positive: number;
  neutral: number;
  negative: number;
  high_sarcasm_evidence: number;
  fusion_statuses: Record<string, number>;
}

export interface NetworkSummaryResponse {
  run_id: number;
  scope_type: string;
  topic_id?: number | null;
  node_count: number;
  edge_count: number;
  density: number;
  weak_component_count: number;
  strong_component_count: number;
  largest_weak_component_size: number;
  connected_user_count: number;
  isolated_user_count: number;
  community_count: number;
  is_sparse: boolean;
  sparsity_warning?: string | null;
  created_at: string;
}

export interface NetworkNodeItem {
  user_id: number;
  username: string;
  pagerank_score: number;
  in_degree: number;
  out_degree: number;
  weighted_in_degree: number;
  weighted_out_degree: number;
  betweenness_centrality: number;
  community_id: number | null;
  cross_community_edge_count: number;
  communities_reached: number;
}

export interface NetworkEdgeItem {
  source_user_id: number;
  source_username: string;
  target_user_id: number;
  target_username: string;
  total_weight: number;
  reply_count: number;
  mention_count: number;
  repost_count: number;
  quote_count: number;
  first_observed_at?: string | null;
  last_observed_at?: string | null;
}

export interface CommunityItem {
  community_id: number;
  user_count: number;
  interaction_count: number;
  top_users: NetworkNodeItem[];
}

export interface CommunityFlowItem {
  source_community_id: number;
  target_community_id: number;
  interaction_count: number;
  first_observed_at?: string | null;
  last_observed_at?: string | null;
}

export interface TopicNetworkResponse {
  available: boolean;
  reason?: string | null;
  run?: NetworkSummaryResponse | null;
  nodes: NetworkNodeItem[];
  edges: NetworkEdgeItem[];
  communities: CommunityItem[];
  flows: CommunityFlowItem[];
  top_pagerank_nodes: NetworkNodeItem[];
  top_bridge_nodes: NetworkNodeItem[];
}

export interface TweetSentimentInfo {
  final_sentiment: string;
  final_confidence: number;
  sarcasm_score?: number | null;
  high_sarcasm_evidence: boolean;
  fusion_status?: string | null;
}

export interface TweetTopicInfo {
  topic_id: number;
  label: string;
  topic_type: string;
}

export interface TweetItem {
  id: number;
  tweet_id: string;
  username: string;
  text: string;
  created_at_utc: string;
  ingested_at: string;
  like_count: number;
  retweet_count: number;
  reply_count: number;
  quote_count: number;
  sentiment?: TweetSentimentInfo | null;
  topic?: TweetTopicInfo | null;
}

export interface TweetListResponse {
  items: TweetItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PipelineDimensionStatus {
  status: string;
  is_available: boolean;
  records_count: number;
  latest_run_at?: string | null;
  pipeline_version?: string | null;
  notes?: string | null;
}

export interface SystemAnalysisStatusResponse {
  generated_at: string;
  collection: PipelineDimensionStatus;
  sentiment: PipelineDimensionStatus;
  sarcasm: PipelineDimensionStatus;
  trends: PipelineDimensionStatus;
  network: PipelineDimensionStatus;
  demographics: PipelineDimensionStatus;
  emotion: PipelineDimensionStatus;
  stance: PipelineDimensionStatus;
}
