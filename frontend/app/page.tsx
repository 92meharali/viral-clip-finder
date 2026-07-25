"use client";

import { useQuery } from "@tanstack/react-query";

import { AnalyzeForm } from "@/components/analyze-form";
import { ProjectCard } from "@/components/project-card";
import { listProjects } from "@/lib/api";

export default function HomePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["projects"],
    queryFn: () => listProjects(12),
  });

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Find viral moments fast</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Paste a YouTube URL to analyze the transcript, rank the best clips, and export
            timestamps for CapCut, Premiere, or DaVinci Resolve.
          </p>
        </div>
        <AnalyzeForm />
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Recent projects</h2>
          {data ? <span className="text-sm text-muted-foreground">{data.total} total</span> : null}
        </div>

        {isLoading ? <p className="text-sm text-muted-foreground">Loading projects...</p> : null}
        {isError ? (
          <p className="text-sm text-red-500">
            Could not load projects. Make sure the API is running on port 8000.
          </p>
        ) : null}

        {data && data.items.length === 0 ? (
          <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
            No projects yet. Analyze your first YouTube video above.
          </p>
        ) : null}

        {data && data.items.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
