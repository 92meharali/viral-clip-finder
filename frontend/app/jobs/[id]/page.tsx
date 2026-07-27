"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ClipCard } from "@/components/clip-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysisJob } from "@/lib/api";

function stageLabel(stage: string | null): string {
  if (!stage) return "Working";
  return stage.replaceAll("_", " ");
}

function formatJobError(error: string): { title: string; detail: string; hint?: string } {
  if (error.includes("No clip analysis response") || error.includes("AI_ANALYSIS_RESPONSE_PATH")) {
    return {
      title: "Manual AI provider is not supported in the web app",
      detail:
        "This job used the cursor provider, which requires pasting a prompt into Cursor and saving a JSON file by hand.",
      hint: "Set GEMINI_API_KEY in your .env file, restart the API, and analyze again. The website uses Gemini automatically.",
    };
  }

  if (error.includes("Gemini free-tier quota is not available") || error.includes("RESOURCE_EXHAUSTED")) {
    return {
      title: "Gemini quota unavailable",
      detail: error,
      hint: "Get a key from aistudio.google.com/apikey (starts with AIza), set GEMINI_MODEL=gemini-2.5-flash-lite, restart the API, and try again.",
    };
  }

  if (error.includes("Gemini rate limit reached")) {
    return {
      title: "Gemini rate limit",
      detail: error,
      hint: "Wait about a minute, then analyze again.",
    };
  }

  if (error.includes("Gemini API key is not configured")) {
    return {
      title: "Gemini API key required",
      detail: error,
      hint: "Copy .env.example to .env, add your GEMINI_API_KEY, then restart the API server.",
    };
  }

  if (error.includes("OpenAI API key is not configured")) {
    return {
      title: "OpenAI API key required",
      detail: error,
      hint: "Copy .env.example to .env, add your OPENAI_API_KEY, then restart the API server.",
    };
  }

  return { title: "Analysis failed", detail: error };
}

export default function JobPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;

  const { data: job, isError } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getAnalysisJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
  });

  if (isError) {
    return <p className="text-red-500">Failed to load analysis job.</p>;
  }

  if (!job) {
    return <p className="text-muted-foreground">Loading analysis...</p>;
  }

  const isRunning = job.status === "pending" || job.status === "running";
  const isFailed = job.status === "failed";
  const result = job.status === "completed" ? job.result : null;

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <p className="text-sm text-muted-foreground">Analysis job</p>
        <h1 className="text-2xl font-bold">
          {job.result?.title ?? job.video_id ?? "YouTube analysis"}
        </h1>
        <p className="text-sm capitalize text-muted-foreground">
          Status: {job.status}
          {job.stage ? ` · ${stageLabel(job.stage)}` : ""}
        </p>
        {job.progress_message ? (
          <p className="text-sm text-muted-foreground">{job.progress_message}</p>
        ) : null}
      </section>

      {isRunning ? (
        <Card>
          <CardHeader>
            <CardTitle>Analyzing video</CardTitle>
            <CardDescription>
              Fetching transcript, generating candidate windows, and ranking viral moments.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
              <div className="h-full w-1/2 animate-pulse rounded-full bg-primary" />
            </div>
          </CardContent>
        </Card>
      ) : null}

      {isFailed ? (
        <Card className="border-red-500/50">
          {(() => {
            const failure = formatJobError(job.error ?? "Unknown error");
            return (
              <>
                <CardHeader>
                  <CardTitle>{failure.title}</CardTitle>
                  <CardDescription>{failure.detail}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {failure.hint ? (
                    <p className="text-sm text-muted-foreground">{failure.hint}</p>
                  ) : null}
                  <Link href="/">
                    <Button variant="outline">Try another video</Button>
                  </Link>
                </CardContent>
              </>
            );
          })()}
        </Card>
      ) : null}

      {result ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Ranked clips</h2>
              <p className="text-sm text-muted-foreground">
                {result.clips_ranked} clips · {result.llm_windows_analyzed} LLM windows
              </p>
            </div>
            <Link href="/">
              <Button variant="outline">Analyze another</Button>
            </Link>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {result.clips.map((clip) => (
              <ClipCard key={`${clip.rank}-${clip.start}`} clip={clip} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
