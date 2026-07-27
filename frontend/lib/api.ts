import type {
  AnalysisJob,
  ClipListResponse,
  ProjectDetail,
  ProjectListResponse,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function startAnalysis(
  url: string,
  provider: string = "gemini",
): Promise<AnalysisJob> {
  return apiFetch<AnalysisJob>("/analyze", {
    method: "POST",
    body: JSON.stringify({ url, provider }),
  });
}

export async function getAnalysisJob(jobId: string): Promise<AnalysisJob> {
  return apiFetch<AnalysisJob>(`/analyze/${jobId}`);
}

export async function listProjects(limit = 12): Promise<ProjectListResponse> {
  return apiFetch<ProjectListResponse>(`/projects?limit=${limit}`);
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  return apiFetch<ProjectDetail>(`/projects/${projectId}`);
}

export async function listClips(params: {
  project_id?: string;
  emotion?: string;
  min_score?: number;
  limit?: number;
}): Promise<ClipListResponse> {
  const search = new URLSearchParams();
  if (params.project_id) search.set("project_id", params.project_id);
  if (params.emotion) search.set("emotion", params.emotion);
  if (params.min_score !== undefined) search.set("min_score", String(params.min_score));
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  const query = search.toString();
  return apiFetch<ClipListResponse>(`/clips${query ? `?${query}` : ""}`);
}

export function getApiBaseUrl(): string {
  return API_URL;
}
