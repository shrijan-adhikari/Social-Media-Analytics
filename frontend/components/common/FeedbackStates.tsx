import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export function LoadingState({ message = "Loading analytical telemetry..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
      <div className="size-8 rounded-full border-2 border-intel-gold border-t-transparent animate-spin" />
      <p className="text-xs font-mono text-intel-muted tracking-wider uppercase">{message}</p>
    </div>
  );
}

export function ErrorState({
  title = "Backend Connection Error",
  message = "Failed to fetch analytics from the FastAPI read API.",
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-xl border border-intel-red/30 bg-card p-6 text-center max-w-md mx-auto my-8">
      <div className="size-10 rounded-full bg-intel-red/10 text-intel-red flex items-center justify-center mx-auto mb-3">
        <AlertCircle size={20} />
      </div>
      <h3 className="text-sm font-bold text-intel-text mb-1 font-mono">{title}</h3>
      <p className="text-xs text-intel-muted mb-4 leading-relaxed">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-intel-gold/40 bg-card-elevated text-xs font-mono text-intel-gold hover:bg-intel-gold hover:text-black transition-all cursor-pointer"
        >
          <RefreshCw size={14} />
          Retry Connection
        </button>
      )}
    </div>
  );
}
