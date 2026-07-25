"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { startAnalysis } from "@/lib/api";

export function AnalyzeForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const job = await startAnalysis(url.trim());
      router.push(`/jobs/${job.id}`);
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "Failed to start analysis";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          type="url"
          placeholder="Paste a YouTube URL..."
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          required
          aria-label="YouTube URL"
        />
        <Button type="submit" disabled={loading || !url.trim()} className="sm:w-36">
          {loading ? "Starting..." : "Analyze"}
        </Button>
      </div>
      {error ? <p className="text-sm text-red-500">{error}</p> : null}
      <p className="text-sm text-muted-foreground">
        We fetch the transcript, find viral moments with AI, and rank the best clips for your edit.
      </p>
    </form>
  );
}

export function SiteHeader() {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Viral Clip Finder
        </Link>
        <p className="hidden text-sm text-muted-foreground sm:block">
          AI video intelligence, not editing
        </p>
      </div>
    </header>
  );
}
