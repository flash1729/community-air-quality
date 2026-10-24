"use client";

import type { ReactNode } from "react";

const MONO = '"Geist Mono Variable", ui-monospace, monospace';

export const GRID_STROKE = "var(--chart-grid)";
export const CURSOR_LINE = { stroke: "var(--line-strong)", strokeWidth: 1, strokeDasharray: "4 4" };
export const CURSOR_BAND = { fill: "var(--surface-2)" };
export const ACTIVE_DOT = { r: 4.5, strokeWidth: 2, stroke: "var(--surface-solid)" };

export function axisTick(color = "var(--chart-axis)") {
  return { fill: color, fontSize: 11, fontFamily: MONO };
}

/** Splits "11 Nov, 05:00 pm" into the part before and after the comma. */
function splitWhen(label: unknown): [string, string | undefined] {
  const [day, time] = String(label ?? "").split(", ");
  return [day, time];
}

/** Time-axis tick on two lines: the time, then the date underneath. */
export function TimeTick({ x = 0, y = 0, payload }: { x?: number; y?: number; payload?: { value?: unknown } }) {
  const [day, time] = splitWhen(payload?.value);
  return (
    <text x={x} y={y} textAnchor="middle" fontFamily={MONO} fontSize={10.5}>
      <tspan x={x} dy="0.9em" fill="var(--chart-axis)">
        {time ?? day}
      </tspan>
      {time && (
        <tspan x={x} dy="1.3em" fill="rgb(var(--faint))">
          {day}
        </tspan>
      )}
    </text>
  );
}

/** Shared props for a time axis that uses `TimeTick`. */
export const TIME_AXIS = {
  dataKey: "label",
  height: 42,
  minTickGap: 28,
  tickLine: false,
  axisLine: false,
  tickMargin: 8,
  tick: <TimeTick />,
  // Spacing is measured from this shorter text, which is the widest line drawn.
  tickFormatter: (label: unknown) => splitWhen(label)[1] ?? String(label),
} as const;

/** Keeps axis numbers short: 0.001, 12.5, 188, 1250. */
export function tickNumber(value: number): string {
  return String(Number(Number(value).toPrecision(3)));
}

type TipItem = { name?: string | number; value?: unknown; color?: string };

export function ChartTooltip({
  active,
  payload,
  label,
  format,
}: {
  active?: boolean;
  payload?: TipItem[];
  label?: ReactNode;
  format: (value: unknown, name: string) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="min-w-[10rem] rounded-2xl border border-line-strong bg-surface-solid px-3.5 py-3 text-xs shadow-pop">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">{label}</p>
      <ul className="mt-2 space-y-1.5">
        {payload.map((item) => {
          const name = String(item.name ?? "");
          return (
            <li key={name} className="flex items-center justify-between gap-5">
              <span className="flex items-center gap-2 text-muted">
                <span className="h-2 w-2 rounded-full" style={{ background: item.color }} />
                {name}
              </span>
              <span className="font-semibold tabular-nums text-ink">{format(item.value, name)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function isMissing(value: unknown): boolean {
  return value === null || value === undefined || Number.isNaN(Number(value));
}

export function EmptyChart({ children }: { children: ReactNode }) {
  return (
    <div className="pointer-events-none absolute inset-0 grid place-items-center">
      <p className="rounded-full border border-line bg-surface-solid px-4 py-2 text-xs text-muted shadow-pop">{children}</p>
    </div>
  );
}

/** Line swatch plus name, used as a chart legend entry. */
export function LegendKey({
  color,
  dashed = false,
  children,
}: {
  color: string;
  dashed?: boolean;
  children: ReactNode;
}) {
  return (
    <span className="flex items-center gap-2">
      <span
        className="h-0 w-5 shrink-0 border-t-[2.5px]"
        style={{ borderColor: color, borderTopStyle: dashed ? "dashed" : "solid" }}
      />
      <span>{children}</span>
    </span>
  );
}
