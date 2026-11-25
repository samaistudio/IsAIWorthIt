/* eslint-disable @typescript-eslint/no-explicit-any */
export type Month = { month: string; active_users: number; hours_saved: number; benchmark_hours?: number; value_eur: number; spend_eur?: number; net_eur?: number };
export type Role = { role: string; people: number; hidden: boolean; adoption?: number; hours_saved?: number };
export type Tool = { tool: string; seats?: number | null; active_users: number; unused_seats?: number; monthly_cost_eur?: number | null; wasted_eur?: number };
export type Tip = { kind: string; text: string };
export type Business = {
  slug: string; name: string; industry?: string; city?: string; people: number; opted_in: number; month: string; real?: boolean;
  current: Month; months: Month[]; tasks: { task: string; hours_saved: number }[]; tools: Tool[]; roles: Role[];
  kpis?: { name: string; first: number; first_month: string; last: number; last_month: string }[];
  k_min?: number; compare?: { adoption: number }; tips?: Tip[];
  scope?: { level: "management" | "company" | "team" | "everyone"; team?: string };
  measurement?: { method?: string; calibration?: { factor?: number | null; n?: number | null; capped?: boolean };
    evidence?: { name: string; before: number; after: number; change: number; months_before?: number; months_after?: number }[] };
};

export const eur = (v?: number | null) => v == null ? "–" : (v < 0 ? "−" : "") + "€" + Math.abs(Math.round(v)).toLocaleString("en-US");
export const hrs = (v?: number | null) => (v ?? 0).toLocaleString("en-US", { maximumFractionDigits: 1 });
export const monS = (m: string) => new Date(+m.slice(0, 4), +m.slice(5) - 1).toLocaleString("en-US", { month: "short" });
export const monL = (m: string) => new Date(+m.slice(0, 4), +m.slice(5) - 1).toLocaleString("en-US", { month: "long" });
export const seesMoney = (d: Business) => !d.scope || d.scope.level === "management" || d.scope.level === "company";

/** "View as" preview for the dashboard. Report files are filtered in Python before they are written. */
export function scoped(d: Business, role: string): Business {
  if (role === "management") return { ...d, scope: { level: "management" } };
  const noMoney = (m: Month): Month => ({ ...m, spend_eur: undefined, net_eur: undefined });
  if (role === "everyone") return { ...d, scope: { level: "everyone" }, roles: [], kpis: [],
    tools: d.tools.filter(t => t.active_users).map(t => ({ tool: t.tool, active_users: t.active_users })),
    current: noMoney(d.current), months: d.months.map(noMoney), measurement: { ...d.measurement, evidence: [] } };
  const team = d.roles.find(r => r.role === role.slice(5))!, share = team.people / d.people;
  const current = noMoney({ ...d.current, active_users: Math.round((team.adoption ?? 0) * team.people), hours_saved: team.hours_saved ?? 0, benchmark_hours: undefined,
    value_eur: d.current.value_eur * (team.hours_saved ?? 0) / Math.max(.1, d.current.hours_saved) });
  // The demo data only has a team's own numbers for the latest month, so earlier months are estimated from the team's
  // share of headcount (real team report files are built per team in Python). The latest month is the team's own
  // numbers, so chart, monthly fold, what-if and headline all show the same figure for it.
  const months = d.months.map(m => m.month === d.month ? { ...current }
    : noMoney({ ...m, value_eur: m.value_eur * share, hours_saved: +(m.hours_saved * share).toFixed(1), active_users: Math.round(m.active_users * share) }));
  return { ...d, name: `${team.role} · ${d.name}`, people: team.people, opted_in: team.people, scope: { level: "team", team: team.role },
    compare: { adoption: d.current.active_users / d.opted_in }, roles: [team], kpis: [], tools: [], tasks: [], measurement: { ...d.measurement, evidence: [] },
    current, months };
}

export function markdown(d: Business) {
  const c = d.current, money = seesMoney(d), lvl = d.scope?.level ?? "management";
  const cal = d.measurement?.calibration;
  const L = [`# AI use report – ${d.name}`, `Scope: ${lvl === "team" ? `team ${d.scope!.team} (incl. sub-teams)` : lvl}. Month: ${d.month}. People: ${d.people}.`,
    `Numbers are estimates. Time saved = benchmarks per AI action${cal?.factor ? `, calibrated by a staff survey (×${cal.factor})` : ""}.`, "",
    "## This month", `- People using AI: ${c.active_users} of ${d.opted_in}`, `- Hours saved: ${hrs(c.hours_saved)}`, `- Value of time saved: €${Math.round(c.value_eur)}`];
  if (money) L.push(`- Licence costs: €${c.spend_eur}`, `- Net benefit: €${c.net_eur}`);
  if (d.compare) L.push(`- Company average: ${Math.round(d.compare.adoption * 100)}% use AI`);
  L.push("", "## By month", `| Month | People using AI | Hours saved | Value €${money ? " | Costs € | Net €" : ""} |`, `|---|---|---|---${money ? "|---|---" : ""}|`,
    ...d.months.map(m => `| ${m.month} | ${m.active_users} | ${hrs(m.hours_saved)} | ${Math.round(m.value_eur)}${money ? ` | ${m.spend_eur} | ${m.net_eur}` : ""} |`));
  if (d.tasks?.length) L.push("", "## Where time is saved", ...d.tasks.map(t => `- ${t.task}: ${t.hours_saved} h`));
  if (d.roles?.length) L.push("", "## Teams (5+ people only)", ...d.roles.map(r => `- ${r.role}: ${r.hidden ? "not shown" : `${Math.round((r.adoption ?? 0) * 100)}% use AI, ${r.hours_saved} h saved`}`));
  if (money && d.tools?.length) L.push("", "## Licences", ...d.tools.map(t => `- ${t.tool}: ${t.active_users} active${t.seats ? `, ${t.seats} seats, €${t.monthly_cost_eur}/month, ${t.unused_seats} unused` : ""}`));
  (d.measurement?.evidence ?? []).forEach(e => L.push(`- Evidence: ${e.name} per 100 booked hours ${e.before} → ${e.after} (${Math.round(e.change * 100)}%)`));
  if (d.kpis?.length) L.push("", "## Business numbers", ...d.kpis.map(k => `- ${k.name}: ${k.first} (${k.first_month}) → ${k.last} (${k.last_month})`));
  L.push("", "No individual employees are included. Groups under 5 people are left out.");
  return L.join("\n") + "\n";
}

export function download(name: string, text: string, type: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
}

declare global { interface Window { __DATA__?: Business } }
export const REPORT: Business | null = (window as any).__DATA__ ?? null;
