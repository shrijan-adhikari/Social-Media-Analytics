"use client";

import React from "react";
import { Activity, ShieldCheck, RefreshCw } from "lucide-react";

interface HeaderProps {
  lastUpdated?: string | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

const NAV_LINKS = [
  { id: "overview", label: "Overview" },
  { id: "sentiment", label: "Sentiment" },
  { id: "narrative", label: "Narrative" },
  { id: "trends", label: "Trends" },
  { id: "audience", label: "Audience" },
  { id: "network", label: "Network" },
];

export function Header({ lastUpdated, onRefresh, isRefreshing }: HeaderProps) {
  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const formattedTimestamp = lastUpdated
    ? new Date(lastUpdated).toLocaleString("en-US", {
        timeZone: "UTC",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }) + " UTC"
    : "Synchronizing...";

  return (
    <header className="sticky top-0 z-40 border-b border-card-border bg-[#070709]/95 backdrop-blur-md">
      <div className="max-w-[1680px] mx-auto px-4 md:px-8 lg:px-10 py-3 flex items-center justify-between gap-4 flex-wrap">
        {/* Brand */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="size-8 rounded-lg flex items-center justify-center bg-intel-gold text-black shadow-[0_0_12px_rgba(229,185,92,0.3)]">
            <Activity size={18} strokeWidth={2.5} />
          </div>
          <div className="leading-tight">
            <p className="font-bold text-sm tracking-tight text-intel-text">RADAR // ANALYTICS</p>
            <p className="text-[10px] tracking-wider uppercase text-intel-goldLight font-mono">
              Twitter / X Intelligence
            </p>
          </div>
        </div>

        {/* Navigation Anchors */}
        <nav className="flex items-center gap-5 text-xs font-semibold overflow-x-auto font-mono text-intel-muted">
          {NAV_LINKS.map((link) => (
            <button
              key={link.id}
              onClick={() => scrollTo(link.id)}
              className="hover:text-white transition-colors cursor-pointer py-1"
            >
              {link.label}
            </button>
          ))}
        </nav>

        {/* Status Badge & Timestamp (Correction 5) */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-intel-green/40 bg-intel-green/10 text-intel-green">
            <span className="size-2 rounded-full bg-intel-green animate-pulse" />
            <span className="text-[11px] font-bold tracking-wider font-mono">PIPELINE ACTIVE</span>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-intel-muted">
            <span className="hidden sm:inline">Latest Analysis Run:</span>
            <span className="text-intel-text font-bold">{formattedTimestamp}</span>
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isRefreshing}
                title="Refresh analytics from backend"
                className="p-1 rounded hover:bg-card-elevated hover:text-white transition-all cursor-pointer"
              >
                <RefreshCw size={13} className={isRefreshing ? "animate-spin" : ""} />
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
