import type { CoachMessage } from "../../services/types";

interface CoachPanelProps {
  messages: CoachMessage[];
}

export default function CoachPanel({ messages }: CoachPanelProps) {
  return (
    <div className="flex h-full w-[340px] shrink-0 flex-col border-l border-[#f0f0f0] bg-white">
      <div className="flex items-center gap-2 border-b border-[#f0f0f0] px-5 py-4">
        <span className="h-2 w-2 rounded-full bg-[#22c55e]" />
        <span className="text-sm font-semibold text-[#18181b]">Coach</span>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="flex flex-col gap-3">
          {messages.map((msg) => {
            const isHighlight = msg.type === "pattern";
            return (
              <div
                key={msg.id}
                className={`rounded-xl border p-4 ${
                  isHighlight
                    ? "border-[#ede9fe] bg-[#f5f3ff]"
                    : "border-[#f0f0f0] bg-[#fafafa]"
                }`}
              >
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
                  {msg.label}
                </p>
                <p className="text-sm leading-relaxed text-[#3f3f46]">
                  {msg.content}
                </p>
                {msg.actionLabel && (
                  <button className="mt-2 text-sm font-medium text-[#6366f1] hover:text-[#4f46e5]">
                    {msg.actionLabel}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="border-t border-[#f0f0f0] px-5 py-4">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Ask your coach..."
            className="flex-1 rounded-lg border border-[#f0f0f0] bg-[#fafafa] px-3 py-2 text-sm text-[#18181b] placeholder-[#a1a1aa] outline-none focus:border-[#d4d4d8]"
          />
          <button className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#18181b] text-white transition-colors hover:bg-[#27272a]">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2L7 9M14 2L9.5 14L7 9M14 2L2 6.5L7 9" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
