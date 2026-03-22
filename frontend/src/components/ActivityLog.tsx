import { useEffect, useRef } from "react";

export interface LogLine {
  time: string;
  text: string;
  done?: boolean;
}

interface ActivityLogProps {
  lines: LogLine[];
}

export function ActivityLog({ lines }: ActivityLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="card p-4">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Activity Log
      </p>
      <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
        {lines.map((line, i) => (
          <div key={i} className="flex gap-2 items-start">
            <span className="text-gray-400 shrink-0">{line.time}</span>
            <span className={line.done ? "text-green-600" : "text-gray-700"}>
              {line.done ? "✓ " : "⠿ "}
              {line.text}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
