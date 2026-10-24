"use client";

import { CircleAlert, Info, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";

import { categoryStyle } from "@/lib/format";

/** Fixed backdrop. It reads --aqi-current from the nearest `.aqi-scope`. */
export function Ambient() {
  return <div className="ambient" aria-hidden="true" />;
}

/** Renders "PM2.5", "NO2", "O3" with the number as a subscript. */
export function Formula({ name }: { name: string }) {
  const match = /^([A-Za-z]+)([\d.]+)$/.exec(name);
  if (!match) return <>{name}</>;
  return (
    <>
      {match[1]}
      <sub>{match[2]}</sub>
    </>
  );
}

export function SectionHeading({
  icon,
  title,
  hint,
  children,
}: {
  icon?: ReactNode;
  title: ReactNode;
  hint?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
      <div className="flex min-w-0 items-start gap-3">
        {icon && (
          <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-line bg-surface-2 text-accent">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <h2 className="text-base font-semibold tracking-tight text-ink">{title}</h2>
          {hint && <p className="mt-0.5 text-xs leading-5 text-muted">{hint}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

type Option<T extends string> = { id: T; name: string };

/** Pill radio group. Arrow keys move between options. */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
  formula = false,
}: {
  label: string;
  value: T;
  options: readonly Option<T>[];
  onChange: (value: T) => void;
  formula?: boolean;
}) {
  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = (index + step + options.length) % options.length;
    onChange(options[next].id);
    const sibling = event.currentTarget.parentElement?.children[next];
    if (sibling instanceof HTMLElement) sibling.focus();
  }

  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="no-scrollbar inline-flex max-w-full overflow-x-auto rounded-full border border-line bg-surface-2 p-1"
    >
      {options.map((option, index) => {
        const active = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(option.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium transition duration-200 ${
              active ? "bg-ink text-paper shadow-sm" : "text-muted hover:text-ink"
            }`}
          >
            {formula ? <Formula name={option.name} /> : option.name}
          </button>
        );
      })}
    </div>
  );
}

export function Banner({
  tone = "info",
  role = "status",
  children,
}: {
  tone?: "info" | "warn" | "error";
  role?: "status" | "alert";
  children: ReactNode;
}) {
  const tones = {
    info: { icon: <Info size={16} />, color: "rgb(var(--accent))" },
    warn: { icon: <TriangleAlert size={16} />, color: "var(--aqi-moderate-text)" },
    error: { icon: <CircleAlert size={16} />, color: "rgb(var(--danger))" },
  } as const;
  const { icon, color } = tones[tone];
  return (
    <p
      role={role}
      className="flex animate-pop items-start gap-3 rounded-2xl border px-4 py-3 text-sm leading-6 text-ink"
      style={{
        borderColor: `color-mix(in srgb, ${color} 32%, transparent)`,
        background: `color-mix(in srgb, ${color} 9%, var(--surface))`,
      }}
    >
      <span className="mt-1 shrink-0" style={{ color }}>
        {icon}
      </span>
      <span>{children}</span>
    </p>
  );
}

/** Coloured pill for an AQI value and its category. */
export function AqiBadge({
  value,
  category,
  size = "md",
}: {
  value: number | null;
  category: string | null;
  size?: "sm" | "md";
}) {
  const style = categoryStyle(category);
  const available = value !== null && category !== null;
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full font-semibold tabular-nums ${
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"
      }`}
      style={{ background: style.soft, color: style.text }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: style.solid }} />
      {available ? (
        <>
          {value}
          <span className="font-medium opacity-80">{category}</span>
        </>
      ) : (
        "AQI unavailable"
      )}
    </span>
  );
}

export function Skeleton({ className = "", style }: { className?: string; style?: CSSProperties }) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden="true" />;
}

/** Eases a number toward its target. Jumps straight there when motion is reduced. */
export function useCountUp(target: number, duration = 1100): number {
  const [value, setValue] = useState(0);
  const from = useRef(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      from.current = target;
      setValue(target);
      return;
    }
    const start = from.current;
    const began = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - began) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + (target - start) * eased;
      from.current = current;
      setValue(current);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return value;
}
