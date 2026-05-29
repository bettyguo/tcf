import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "neutral" | "accent" | "danger" | "success" | "warning";

const TONE: Record<Tone, string> = {
  neutral: "border-border text-muted",
  accent: "border-accent text-accent",
  danger: "border-danger text-danger",
  success: "border-success text-success",
  warning: "border-warning text-warning",
};

export function Badge({
  tone = "neutral",
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
        TONE[tone],
        className,
      )}
      {...rest}
    >
      {children}
    </span>
  );
}
