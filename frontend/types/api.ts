export type AnalysisJobStatus = "pending" | "running" | "completed" | "failed";

export type AnalysisStage =
  | "ingesting"
  | "generating_windows"
  | "analyzing"
  | "ranking"
  | "finalizing";

export interface ClipSummary {
  rank: number;
  start: string;
  end: string;
  duration_seconds: number;
  viral_score: number;
  rank_score: number;
  emotion: string;
  hook: string;
  reason: string;
  summary: string;
}

export interface AnalysisJobResult {
  video_id: string;
  title: string;
  channel: string | null;
  duration_seconds: number;
  webpage_url: string;
  transcript_language: string;
  transcript_source: string;
  transcript_segments: number;
  candidate_windows: number;
  llm_windows_analyzed: number;
  clips_analyzed: number;
  clips_ranked: number;
  clips: ClipSummary[];
}

export interface AnalysisJob {
  id: string;
  url: string;
  video_id: string | null;
  provider: string;
  top_n: number | null;
  status: AnalysisJobStatus;
  stage: AnalysisStage | null;
  progress_message: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  result: AnalysisJobResult | null;
}

export interface ProjectSummary {
  id: string;
  video_id: string;
  title: string;
  channel: string | null;
  duration_seconds: number;
  webpage_url: string;
  youtube_url: string;
  clip_count: number;
  latest_job_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: ProjectSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProjectDetail extends ProjectSummary {
  transcript_language: string | null;
  transcript_source: string | null;
  clips: ClipSummary[];
}

export interface ClipListResponse {
  items: ClipSummary[];
  total: number;
  limit: number;
  offset: number;
}
