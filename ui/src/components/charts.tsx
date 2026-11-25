import * as React from "react";
import { eur, monL, monS, type Month } from "@/lib/data";

function useWidth<T extends HTMLElement>() {
  const ref = React.useRef<T>(null);
  const [w, setW] = React.useState(600);
  React.useLayoutEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

/** A tidy axis: the top rounded up to 1, 2, 2.5 or 5 × 10^n, three or four ticks. Only the scale changes, never a value. */
export function niceAxis(top: number, integer = false) {
  const rough = Math.max(top, integer ? 3 : 1e-6) / 3, mag = 10 ** Math.floor(Math.log10(rough));
  const steps = [1, 2, 2.5, 5, 10].map(f => f * mag).filter(s => !integer || Number.isInteger(s));
  const step = steps.find(s => s >= rough) ?? 10 * mag;
  const max = Math.max(step, Math.ceil(top / step - 1e-9) * step);
  return { max, ticks: Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step) };
}

export type Series = "money" | "hours" | "people";

/** Plain bar chart: square bars, round axis steps, optional dashed licence line.
 *  The first `estimated` months are drawn as outlines (estimates, not measured numbers).
 *  With the licence line, the part of a bar that only covers the licences is a light tint and the part above it is full colour.
 *  Each month can be hovered, focused or tapped for its numbers. */
export function MonthChart({ months, series, showCost, estimated = 0 }: { months: Month[]; series: Series; showCost: boolean; estimated?: number }) {
  const [ref, w] = useWidth<HTMLDivElement>();
  const [hover, setHover] = React.useState<number | null>(null);
  const cost = series === "money" && showCost;
  const W = Math.max(280, w), wide = W >= 600, H = W < 500 ? 210 : 270, L = 56, R = cost ? (wide ? 104 : 64) : 0, T = 24, B = 28;
  const val = (m: Month) => series === "money" ? m.value_eur : series === "hours" ? m.hours_saved : m.active_users;
  const fmt = (v: number) => series === "money" ? eur(v) : series === "hours" ? `${v.toLocaleString("en-US", { maximumFractionDigits: 1 })} h` : `${Math.round(v)}`;
  const top = Math.max(...months.map(m => Math.max(val(m), cost ? m.spend_eur ?? 0 : 0)), 0);
  const { max, ticks } = niceAxis(top, series === "people");
  const step = (W - L - R) / months.length, y = (v: number) => H - B - (v / max) * (H - T - B);
  const h = hover === null ? null : months[hover];
  const last = months.length - 1;
  const what = series === "money" ? "Value of time saved" : series === "hours" ? "Hours saved" : "People using AI";
  const label = (m: Month, i: number) => (i < estimated ? "Estimate. " : "") + (series === "money"
    ? `${monL(m.month)}: ${eur(m.value_eur)} saved${cost ? `, ${eur(m.spend_eur)} licences, net ${eur(m.net_eur)}` : ""}`
    : `${monL(m.month)}: ${fmt(val(m))}`);
  return (
    <div ref={ref} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="group" aria-label={`${what}, by month`} onMouseLeave={() => setHover(null)}>
        {ticks.map(t => (
          <g key={t} aria-hidden>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="stroke-border" />
            <text x={L - 8} y={y(t) + 4} textAnchor="end" className="fill-muted-foreground text-[13px]">{fmt(t)}</text>
          </g>
        ))}
        {months.map((m, i) => {
          const x = L + i * step, v = val(m), c = cost ? Math.min(v, m.spend_eur ?? 0) : 0;
          return (
            <g key={m.month} tabIndex={0} role="img" aria-label={label(m, i)} className="outline-none [&:focus-visible>rect:first-child]:fill-muted"
              onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} onClick={() => setHover(o => o === i ? null : i)}>
              <rect x={x} y={T} width={step} height={H - T - B} className={hover === i ? "fill-muted" : "fill-transparent"} />
              {c > 0 && <rect x={x + step * .25} y={y(c)} width={step * .5} height={Math.max(0, H - B - y(c))} className="fill-accent-1 opacity-40" />}
              {i < estimated
                ? <rect x={x + step * .25 + .75} y={y(v) + .75} width={Math.max(0, step * .5 - 1.5)} height={Math.max(0, y(c) - y(v) - .75)} strokeWidth={1.5} className="fill-transparent stroke-accent-1" />
                : <rect x={x + step * .25} y={y(v)} width={step * .5} height={Math.max(0, y(c) - y(v))} className="fill-accent-1" />}
              <text x={x + step / 2} y={H - 9} textAnchor="middle" className={hover === i ? "fill-foreground text-[13px]" : "fill-muted-foreground text-[13px]"}>{monS(m.month)}</text>
              {i === last && <text x={x + step / 2} y={(cost && Math.abs(y(v) - 8 - y(m.spend_eur ?? 0)) < 14 ? Math.min(y(v), y(m.spend_eur ?? 0)) : y(v)) - 8} textAnchor="middle" className="fill-foreground text-[13px] font-medium" aria-hidden>{fmt(v)}</text>}
            </g>
          );
        })}
        {cost && <>
          <polyline fill="none" strokeWidth={1.5} strokeDasharray="5 4" className="pointer-events-none stroke-line" aria-hidden
            points={[`${L},${y(months[0].spend_eur ?? 0)}`, ...months.map((m, i) => `${L + i * step + step / 2},${y(m.spend_eur ?? 0)}`), `${W - R},${y(months[last].spend_eur ?? 0)}`].join(" ")} />
          {wide ? <text x={W - R + 10} y={y(months[last].spend_eur ?? 0) + 4} className="fill-muted-foreground text-[13px]" aria-hidden>licences {eur(months[last].spend_eur)}</text>
            : <text x={W - R + 8} y={y(months[last].spend_eur ?? 0) - 4} className="fill-muted-foreground text-[13px]" aria-hidden>
              <tspan x={W - R + 8}>licences</tspan><tspan x={W - R + 8} dy={16}>{eur(months[last].spend_eur)}</tspan></text>}
        </>}
      </svg>
      {h && hover !== null && (
        <div className="pointer-events-none absolute top-0 border border-[var(--ctl-border)] bg-background px-3 py-2 t-small tabular-nums sm:whitespace-nowrap"
          style={W < 500 ? { left: L, right: 0 } : hover < months.length / 2 ? { left: L + hover * step } : { right: W - (L + (hover + 1) * step) }}>
          <div className="font-medium">{monL(h.month)}{hover < estimated && <span className="font-normal text-muted-foreground"> · estimate</span>}</div>
          {series === "money"
            ? <div className="text-muted-foreground">Saved {eur(h.value_eur)}{cost && <> · licences {eur(h.spend_eur)} · net {eur(h.net_eur)}</>}</div>
            : <div className="text-muted-foreground">{fmt(val(h))}</div>}
        </div>
      )}
    </div>
  );
}
