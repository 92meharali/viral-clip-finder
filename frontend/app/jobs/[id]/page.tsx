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
  const isComplete = job.status === "completed" && job.result;

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
          <CardHeader>
            <CardTitle>Analysis failed</CardTitle>
            <CardDescription>{job.error ?? "Unknown error"}</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/">
              <Button variant="outline">Try another video</Button>
            </Link>
          </CardContent>
        </Card>
      ) : null}

      {isComplete ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Ranked clips</h2>
              <p className="text-sm text-muted-foreground">
                {job.result.clips_ranked} clips · {job.result.llm_windows_analyzed} LLM windows
              </p>
            </div>
            <Link href="/">
              <Button variant="outline">Analyze another</Button>
            </Link>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {job.result.clips.map((clip) => (
              <ClipCard key={`${clip.rank}-${clip.start}`} clip={clip} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
