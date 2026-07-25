import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { SiteHeader } from "@/components/analyze-form";
import { Providers } from "@/components/providers";

import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Viral Clip Finder",
  description: "Find the best viral moments in long-form YouTube videos with AI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <SiteHeader />
          <main className="mx-auto min-h-[calc(100vh-4rem)] max-w-6xl px-4 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
