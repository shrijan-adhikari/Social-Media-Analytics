import React from "react";
import { Users, AlertCircle } from "lucide-react";

export function AudienceSection() {
  return (
    <section id="audience" className="scroll-mt-24 py-4 border-t border-[#1C1A20] font-mono">
      <div className="rounded-xl border border-card-border bg-[#0C0B10] p-4 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg bg-intel-gold/10 text-intel-gold flex items-center justify-center shrink-0">
            <Users size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white">AUDIENCE DEMOGRAPHIC PROFILING</span>
              <span className="text-[10px] px-2 py-0.2 rounded bg-card-dark border border-card-border text-intel-muted uppercase">
                Phase 5 Scheduled
              </span>
            </div>
            <p className="text-[11px] text-intel-muted mt-0.5 leading-relaxed">
              M3-Inference multimodal demographic inference (age cohorts, gender, language, geo) is scheduled for Phase 5 per PROJECT_CONTEXT.md. Zero demographic data is fabricated.
            </p>
          </div>
        </div>

        <div className="text-[11px] text-intel-muted bg-card-dark px-3 py-1.5 rounded-lg border border-card-border shrink-0">
          Status: <strong className="text-intel-gold">Unavailable in Current Analysis Run</strong>
        </div>
      </div>
    </section>
  );
}
