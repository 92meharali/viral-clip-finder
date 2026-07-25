import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDuration } from "@/lib/utils";
import type { ProjectSummary } from "@/types/api";

interface ProjectCardProps {
  project: ProjectSummary;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link href={`/projects/${project.id}`}>
      <Card className="h-full transition-colors hover:border-primary/50">
        <CardHeader>
          <CardTitle className="line-clamp-2">{project.title}</CardTitle>
          <CardDescription>
            {project.channel ?? "Unknown channel"} · {formatDuration(project.duration_seconds)}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{project.clip_count} clips</span>
            <span className="rounded-full bg-secondary px-2 py-1 text-xs font-medium capitalize">
              {project.latest_job_status ?? "unknown"}
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
