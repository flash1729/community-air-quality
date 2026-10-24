"use client";

import { AQI_MAX, AQI_SCALE, categoryStyle } from "@/lib/format";
import { useCountUp } from "@/components/ui";

const CX = 150;
const CY = 150;
const RADIUS = 110;
const STROKE = 14;
const START = 150; // degrees, lower left
const SWEEP = 240; // degrees, clockwise to lower right
const GAP = 1.1; // degrees trimmed from each side of a band

function angleFor(value: number) {
  return START + (Math.max(0, Math.min(AQI_MAX, value)) / AQI_MAX) * SWEEP;
}

function point(angle: number, radius = RADIUS) {
  const radians = (angle * Math.PI) / 180;
  return { x: CX + radius * Math.cos(radians), y: CY + radius * Math.sin(radians) };
}

function arc(from: number, to: number) {
  const a = point(from);
  const b = point(to);
  const large = to - from > 180 ? 1 : 0;
  return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} A ${RADIUS} ${RADIUS} 0 ${large} 1 ${b.x.toFixed(2)} ${b.y.toFixed(2)}`;
}

// Band edges on the dial: 0, 50, 100, 200, 300, 400, 500.
const BANDS = AQI_SCALE.map((band, index) => ({
  category: band.category,
  from: index === 0 ? 0 : band.min - 1,
  to: band.max,
}));
const TICKS = [0, ...BANDS.map((band) => band.to)];

export function AqiGauge({
  value,
  category,
  available,
}: {
  value: number | null;
  category: string | null;
  available: boolean;
}) {
  const target = available && value !== null ? value : 0;
  const shown = useCountUp(target);
  const current = categoryStyle(available ? category : null);
  const knob = point(angleFor(shown));

  return (
    <div className="relative mx-auto w-full max-w-[21rem]">
      <svg
        viewBox="0 0 300 226"
        className="block w-full"
        role="img"
        aria-label={available ? `AQI ${value}, ${category}, on a scale from 0 to 500` : "AQI unavailable"}
      >
        {BANDS.map((band) => {
          const from = angleFor(band.from) + (band.from === 0 ? 0 : GAP);
          const to = angleFor(band.to) - (band.to === AQI_MAX ? 0 : GAP);
          const color = categoryStyle(band.category).solid;
          const reached = available ? Math.min(to, angleFor(shown)) : from;
          return (
            <g key={band.category}>
              <path d={arc(from, to)} fill="none" stroke={color} strokeOpacity={0.2} strokeWidth={STROKE} />
              {reached > from + 0.2 && (
                <path d={arc(from, reached)} fill="none" stroke={color} strokeWidth={STROKE} />
              )}
            </g>
          );
        })}

        {TICKS.map((tick) => {
          const spot = point(angleFor(tick), RADIUS + 19);
          return (
            <text
              key={tick}
              x={spot.x}
              y={spot.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-faint font-mono"
              fontSize={9}
            >
              {tick}
            </text>
          );
        })}

        {available && (
          <g style={{ filter: `drop-shadow(0 0 7px ${current.solid})` }}>
            <circle cx={knob.x} cy={knob.y} r={11} fill="var(--surface-solid)" />
            <circle cx={knob.x} cy={knob.y} r={7} fill={current.solid} />
          </g>
        )}
      </svg>

      <div className="pointer-events-none absolute inset-x-0 top-[31%] flex flex-col items-center text-center">
        <span className="eyebrow">AQI</span>
        <span
          className={`mt-1 text-[4.6rem] leading-none tracking-[-0.045em] ${
            available ? "font-semibold text-ink" : "font-extralight text-faint"
          }`}
        >
          {available ? Math.round(shown) : "—"}
        </span>
        <span
          className="mt-3 rounded-full px-3.5 py-1 text-sm font-semibold"
          style={{ background: current.soft, color: current.text }}
        >
          {available ? category : "Unavailable"}
        </span>
      </div>
    </div>
  );
}
