import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatScore } from "@/lib/utils";
import type { ClipSummary } from "@/types/api";

interface ClipCardProps {
  clip: ClipSummary;
}

const emotionEmoji: Record<string, string> = {
  humor: "😂",
  funny: "😂",
  shock: "😱",
  betrayal: "🔥",
  suspense: "😬",
  strategy: "🧠",
  accusation: "👀",
};

export function ClipCard({ clip }: ClipCardProps) {
  const emoji = emotionEmoji[clip.emotion.toLowerCase()] ?? "✨";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{clip.hook}</CardTitle>
            <CardDescription>
              #{clip.rank} · {clip.start} → {clip.end} · {clip.duration_seconds.toFixed(0)}s
            </CardDescription>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">{formatScore(clip.viral_score)}</p>
            <p className="text-xs text-muted-foreground">viral score</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-sm">
          <span>{emoji}</span>
          <span className="capitalize">{clip.emotion}</span>
          <span className="text-muted-foreground">· rank {formatScore(clip.rank_score)}</span>
        </div>
        <p className="text-sm text-muted-foreground">{clip.reason}</p>
        <p className="text-sm">{clip.summary}</p>
      </CardContent>
    </Card>
  );
}
