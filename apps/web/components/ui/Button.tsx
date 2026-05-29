// Button primitive (shadcn convention: copied, not depended-on).
// Tap-target floor: 44×44 px (phase8_design.md §1.4 / ADR-044).

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const VARIANT: Record<Variant, string> = {
  primary: "bg-accent text-white hover:opacity-90",
  secondary: "bg-card border border-border text-fg hover:bg-card/70",
  ghost: "bg-transparent text-fg hover:bg-card",
  danger: "bg-danger text-white hover:opacity-90",
};

const SIZE: Record<Size, string> = {
  sm: "min-h-tap px-3 text-sm",
  md: "min-h-tap px-4 text-base",
  lg: "min-h-tap px-6 text-lg",
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { className, variant = "primary", size = "md", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium",
        "transition disabled:opacity-50 disabled:pointer-events-none",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        VARIANT[variant],
        SIZE[size],
        className,
      )}
      {...rest}
    />
  );
});
