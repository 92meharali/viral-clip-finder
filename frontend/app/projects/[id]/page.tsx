"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ClipCard } from "@/components/clip-card";
import { Button } from "@/components/ui/button";
import { getProject } from "@/lib/api";
import { formatDuration } from "@/lib/utils";

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  const { data: project, isLoading, isError } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  if (isLoading) {
    return <p className="text-muted-foreground">Loading project...</p>;
  }

  if (isError || !project) {
    return <p className="text-red-500">Project not found.</p>;
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <Link href="/">
          <Button variant="ghost" className="px-0">
            ← Back to home
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{project.title}</h1>
          <p className="mt-2 text-muted-foreground">
            {project.channel ?? "Unknown channel"} · {formatDuration(project.duration_seconds)} ·{" "}
            {project.clip_count} clips
          </p>
        </div>
        <a
          href={project.webpage_url}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-primary hover:underline"
        >
          Open on YouTube
        </a>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Ranked clips</h2>
        {project.clips.length === 0 ? (
          <p className="text-sm text-muted-foreground">No clips stored for this project yet.</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {project.clips.map((clip) => (
              <ClipCard key={`${clip.rank}-${clip.start}`} clip={clip} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
