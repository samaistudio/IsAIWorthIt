import * as React from "react";
import { MonthChart } from "@/components/charts";
import { cn } from "@/lib/utils";
import { type Business, REPORT, download, eur, markdown, monL, monS, scoped, seesMoney } from "@/lib/data";

type Connector = { key: string; label: string; kind: string; provides: string; how: string; status: string; enabled: boolean; sample?: boolean;
  last?: { ok: number; rows: number; at?: string; message?: string } | null };

const neg = (v?: number | null) => (v ?? 0) < 0;
const NB = " ";
/** Display only: hours always with one decimal ("23.0 h"). The export keeps its own format. */
const hr = (v?: number | null) => (v ?? 0).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const signed = (v?: number | null) => ((v ?? 0) > 0 ? "+" : "") + eur(v);
const params = new URLSearchParams(location.search);
const IN_FRAME = (() => { try { return window.top !== window.self; } catch { return true; } })();
/** ?compact=1 (for a short embed): the open parts below the chart start as closed rows. */
const COMPACT = params.get("compact") === "1";
const FROM_PORTFOLIO = params.get("from") === "portfolio" && !IN_FRAME;
const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Scroll to a part of the overview, open it if it is a fold, and mark it for a moment. */
function jump(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el instanceof HTMLDetailsElement) el.open = true;
  const still = reducedMotion();
  el.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
  if (still) return;
  el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1500);
}

/** "+€120 vs Oct", or "same as Oct" */
function change(now: number | undefined, prev: number | undefined, prevMonth: string | undefined, fmt: (v: number) => string) {
  if (now == null || prev == null || !prevMonth) return null;
  if (now === prev) return `same as ${monS(prevMonth)}`;
  return `${now > prev ? "+" : "−"}${fmt(Math.abs(now - prev))} vs ${monS(prevMonth)}`;
}

/** One row that opens on click. The browser's own <details>: works by keyboard, no animation. */
function Fold({ id, title, note, children }: { id: string; title: string; note?: React.ReactNode; children: React.ReactNode }) {
  return (
    <details id={id} data-iaw={id} className="group scroll-mt-4 border-b">
      <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-3 [&::-webkit-details-marker]:hidden">
        <h2 className="t-h2 wordlink group-hover:underline group-hover:decoration-current">{title}</h2>
        <span className="t-small flex items-center gap-4 text-right text-muted-foreground">
          {note && <span className="hidden sm:inline">{note}</span>}
          <span className="grid h-11 w-11 shrink-0 place-items-center border border-[var(--ctl-border)] text-lg text-foreground group-hover:border-foreground" aria-hidden>
            <span className="group-open:hidden">+</span><span className="hidden group-open:inline">−</span>
          </span>
        </span>
      </summary>
      <div className="pb-8 pt-2">{children}</div>
    </details>
  );
}

/** A part of the overview that is always open. */
function Part({ id, title, note, children }: { id: string; title: string; note?: React.ReactNode; children: React.ReactNode }) {
  if (COMPACT) return <Fold id={id} title={title} note={note}>{children}</Fold>;
  return (
    <section id={id} data-iaw={id} className="scroll-mt-4 border-b py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 className="t-h2">{title}</h2>
        {note && <p className="t-small text-muted-foreground">{note}</p>}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Table({ head, rows, note, left = [0], fixed }: { head: React.ReactNode[]; rows: React.ReactNode[][]; note?: string; left?: number[]; fixed?: string[] }) {
  return (
    <div className="overflow-x-auto">
      <table className={cn("w-full", fixed && "table-fixed")}>
        {fixed && <colgroup>{fixed.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>}
        <thead><tr className="border-b text-left text-muted-foreground">{head.map((h, i) => <th key={i} className={cn("t-label py-2 pr-4 align-bottom last:pr-0", !left.includes(i) && "text-right tabular-nums")}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i} className="border-b last:border-0">{r.map((v, j) => <td key={j} className={cn("py-3 pr-4 align-top last:pr-0", !left.includes(j) && "text-right tabular-nums")}>{v}</td>)}</tr>)}</tbody>
      </table>
      {note && <p className="t-small mt-3 text-muted-foreground">{note}</p>}
    </div>
  );
}

/** A table on wide screens; one block per column on phones (no sideways scrolling). */
function Matrix({ cols, rows, widths }: { cols: string[]; rows: [string, ...React.ReactNode[]][]; widths?: string[] }) {
  const dim = (v: React.ReactNode) => v === "–" || v === "never" || v === "removed";
  const cell = (v: React.ReactNode) => <span className={dim(v) ? "text-muted-foreground" : ""}>{v}</span>;
  return <>
    <div className="hidden sm:block"><Table fixed={widths} head={["", ...cols]} left={cols.map((_, i) => i + 1).concat(0)} rows={rows.map(([l, ...v]) => [<span className="font-medium">{l}</span>, ...v.map(cell)])} /></div>
    <div className="grid gap-8 sm:hidden">
      {cols.map((c, ci) => (
        <div key={c}>
          <h3 className="t-h2 border-b pb-2">{c}</h3>
          <dl>{rows.map(([l, ...v]) => <div key={l} className="grid grid-cols-[minmax(0,9rem)_1fr] gap-4 border-b py-3"><dt className="text-muted-foreground">{l}</dt><dd>{cell(v[ci])}</dd></div>)}</dl>
        </div>
      ))}
    </div>
  </>;
}

/** Name, a thin bar, the number. On phones the bar sits under the name. */
function BarRow({ name, share, value, sub, wide }: { name: React.ReactNode; share: number; value: React.ReactNode; sub?: React.ReactNode; wide?: boolean }) {
  return (
    <li className={cn("grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-2 border-b py-3 last:border-0", wide ? "sm:grid-cols-[minmax(0,13rem)_1fr_11rem]" : "sm:grid-cols-[minmax(0,13rem)_1fr_5rem]")}>
      <span className="col-start-1 row-start-1">{name}</span>
      <span className="col-span-2 col-start-1 row-start-2 h-1.5 bg-muted sm:col-span-1 sm:col-start-2 sm:row-start-1" aria-hidden>
        <span className="block h-full bg-accent-1" style={{ width: `${Math.max(0, Math.min(1, share)) * 100}%` }} />
      </span>
      <span className="col-start-2 row-start-1 text-right tabular-nums sm:col-start-3">{value}{sub && <span className="text-muted-foreground"> {sub}</span>}</span>
    </li>
  );
}

/** Seats as small squares: filled = used, outlined = paid for but unused. */
function Seats({ used, seats }: { used: number; seats: number }) {
  if (seats > 80) return null;
  return (
    <span className="flex flex-wrap gap-[3px]" role="img" aria-label={`${used} of ${seats} seats used`}>
      {Array.from({ length: seats }, (_, i) => <span key={i} className={cn("h-2.5 w-2.5 border", i < used ? "border-accent-1 bg-accent-1" : "border-[var(--ctl-border)]")} />)}
    </span>
  );
}

function ExportMenu({ data, onPreview }: { data: Business; onPreview: () => void }) {
  const [open, setOpen] = React.useState(false);
  const [msg, setMsg] = React.useState("");
  React.useEffect(() => {
    const close = () => setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("click", close); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("click", close); document.removeEventListener("keydown", esc); };
  }, []);
  const name = `is-ai-worth-it-${data.slug}-${data.month}`;
  const act = async (k: string) => {
    if (k === "copy") {
      const t = "Here is our AI usage report. Please analyse it and tell me what stands out.\n\n" + markdown(data);
      try { await navigator.clipboard.writeText(t); setMsg("Copied. Paste it into your AI assistant."); } catch { download(name + ".md", t, "text/markdown"); }
      setTimeout(() => setMsg(""), 2400);
    }
    if (k === "preview") onPreview();
    if (k === "md") download(name + ".md", markdown(data), "text/markdown");
    if (k === "json") download(name + ".json", JSON.stringify(data, null, 1), "application/json");
    setOpen(false);
  };
  return (
    <div className="relative" onClick={e => e.stopPropagation()}>
      <button onClick={() => setOpen(o => !o)} aria-expanded={open} aria-haspopup="menu" className="ctl w-full sm:w-auto">Export for AI</button>
      {open && (
        <div role="menu" className="absolute right-0 z-20 mt-2 w-full border border-[var(--ctl-border)] bg-background sm:w-80">
          {[["copy", "Copy as text for an AI assistant"], ["preview", "Show the text"], ["md", "Download as Markdown"], ["json", "Download the data (JSON)"]].map(([k, label]) => (
            <button key={k} role="menuitem" onClick={() => act(k)} className="block min-h-11 w-full px-3 text-left hover:bg-muted">{label}</button>
          ))}
          <p className="t-label border-t px-3 py-2 font-normal text-muted-foreground">Only what this view shows is exported.</p>
        </div>
      )}
      {msg && <div role="status" className="fixed bottom-6 left-1/2 z-30 -translate-x-1/2 border border-foreground bg-background px-4 py-3">{msg}</div>}
    </div>
  );
}

function Preview({ data, onClose }: { data: Business; onClose: () => void }) {
  return (
    <section className="mb-10 border border-[var(--ctl-border)]" aria-label="Text for an AI assistant">
      <div className="flex items-center justify-between gap-4 border-b px-4 py-2">
        <h2 className="t-h2">Text for an AI assistant</h2>
        <button onClick={onClose} className="ctl">Close</button>
      </div>
      <pre className="t-small max-h-96 overflow-auto whitespace-pre-wrap px-4 py-4 font-mono">{markdown(data)}</pre>
      <p className="t-small border-t px-4 py-3 text-muted-foreground">The same data is available to Claude, Cursor or Copilot through a read-only MCP server (<code>python3 isaiworthit.py mcp</code>).</p>
    </section>
  );
}

const Select = (props: React.SelectHTMLAttributes<HTMLSelectElement>) => (
  <select {...props} className={cn("ctl w-full min-w-0 truncate sm:w-auto sm:max-w-[19rem] lg:max-w-none", props.className)} />
);

function Overview({ d, story, aside }: { d: Business; story: { slug: string; text: string } | null; aside?: React.ReactNode }) {
  const c = d.current, p = d.months[d.months.length - 2], money = seesMoney(d), lvl = d.scope?.level ?? "management";
  const cal = d.measurement?.calibration ?? {}, k = d.k_min ?? 5, used = !!cal.factor;
  const avgRate = c.hours_saved ? c.value_eur / c.hours_saved : 45;
  // null = the hourly cost behind the headline, unrounded, so the default what-if equals the headline exactly
  const [txt, setTxt] = React.useState<string | null>(null);
  React.useEffect(() => setTxt(null), [d.slug, d.scope?.level, d.scope?.team]);
  const rate = txt == null ? null : Math.max(0, parseFloat(txt.replace(",", ".")) || 0);
  const r = rate ?? avgRate, whatIfValue = c.hours_saved * r, whatIfNet = whatIfValue - (c.spend_eur ?? 0);
  const bh = c.benchmark_hours ?? (used ? c.hours_saved / (cal.factor as number) : c.hours_saved);
  const waste = d.tools.reduce((a, t) => a + (t.wasted_eur ?? 0), 0);
  const avg = d.compare ? d.compare.adoption : c.active_users / Math.max(1, d.opted_in);
  const visibleRoles = d.roles.filter(x => !x.hidden);
  const tips = money ? (d.tips ?? []).slice(0, 3) : [];
  const fictional = !d.real;
  const pct = (f: number) => `${f >= 1 ? "+" : "−"}${Math.abs(Math.round((f - 1) * 100))}%`;
  const calcNote = lvl === "team" ? "benchmarks, with the company-wide survey correction"
    : used ? `benchmarks, corrected ${pct(cal.factor as number)} by ${cal.n} survey answers`
      : `benchmarks only: fewer than ${k} survey answers`;

  // since when has every month paid for its licences?
  const nets = d.months.map(m => m.net_eur ?? 0);
  let from = nets.length; while (from > 0 && nets[from - 1] > 0) from--;
  const payNote = !money ? null : from === 0 ? "The time saved was worth more than the licences in every month shown."
    : from < nets.length ? `The time saved has been worth more than the licences every month since ${monL(d.months[from].month)}.`
      : neg(c.net_eur) ? `In ${monL(d.month)} the licences cost more than the time saved was worth.` : null;

  // a team's earlier months are a headcount-share estimate, so no "vs last month" line in the team view
  const ch = (now: number | undefined, prev: number | undefined, f: (v: number) => string) => lvl === "team" ? null : change(now, prev, p?.month, f);
  const numbers: [string, React.ReactNode, (string | null)[]][] = [
    ["Hours saved", `${hr(c.hours_saved)} h`, [ch(c.hours_saved, p?.hours_saved, v => hr(v) + " h")]],
    ["People using AI", <span className="whitespace-nowrap">{c.active_users}<span className="text-muted-foreground"> / {d.opted_in}</span></span>,
      [ch(c.active_users, p?.active_users, String), d.opted_in < d.people ? `${d.opted_in} of ${d.people} agreed to be counted` : null]],
    money
      ? ["Unused licences", waste ? eur(waste) : "None", [waste ? `of ${eur(c.spend_eur)} a month` : "every seat used"]]
      : d.compare
        ? ["Company average", `${Math.round(avg * 100)}%`, ["of people use AI"]]
        : ["Value of time saved", eur(c.value_eur), [ch(c.value_eur, p?.value_eur, eur)]],
  ];

  const questions: [string, string][] = ([
    [money ? "Did AI pay off?" : "How much time did AI save?", "pay"],
    [money && d.tools.some(t => t.unused_seats) ? "Where is money wasted?" : "", "licences"],
    [visibleRoles.length > 1 ? "Which team needs help?" : "", "teams"],
    [d.tasks.length ? "Where is the time saved?" : "", "tasks"],
    ["How are the hours counted?", "calc"],
  ] as [string, string][]).filter(([q]) => q);

  const nUsing = visibleRoles.filter(x => (x.adoption ?? 0) > 0).length, nTeams = visibleRoles.length, nAll = d.roles.length, nSmall = nAll - nTeams;
  const teamsUsing = nSmall ? `${nTeams} of ${nAll} teams shown · ${nSmall} under ${k} people`
    : nUsing === nTeams ? (nTeams === 1 ? "One team uses AI" : nTeams === 2 ? "Both teams use AI" : `All ${nTeams} teams use AI`) : `${nUsing} of ${nTeams} teams use AI`;
  const maxTask = Math.max(...d.tasks.map(t => t.hours_saved), 0.1);
  // team view: only the latest month is the team's own number, earlier months are a headcount-share estimate
  const estimated = lvl === "team" ? d.months.length - 1 : 0;

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="t-small text-muted-foreground">{[`${d.name}${fictional ? " (fictional)" : ""}`, [d.industry, d.city].filter(Boolean).join(", "), `${d.people} people`].filter(Boolean).join(" · ")}</p>
        {aside}
      </div>

      <h1 className="t-h1 mt-3" data-iaw="headline">
        {money ? <>
          <span className="hidden sm:inline">{monL(d.month)}: {eur(c.value_eur)}{NB}saved −{NB}{eur(c.spend_eur)}{NB}licences ={NB}<span className={neg(c.net_eur) ? "text-destructive" : "text-accent-1"}>{eur(c.net_eur)}</span></span>
          <span className="sm:hidden">{monL(d.month)}: <span className={neg(c.net_eur) ? "text-destructive" : "text-accent-1"}>{signed(c.net_eur)}{NB}net</span>
            <span className="mt-2 block text-base font-normal tracking-normal text-muted-foreground">{eur(c.value_eur)}{NB}saved −{NB}{eur(c.spend_eur)}{NB}licences</span></span>
        </> : <>{monL(d.month)}: <span className="text-accent-1">{hr(c.hours_saved)}{NB}hours</span> saved{lvl === "team" ? ` in ${d.scope!.team}` : ""}</>}
      </h1>

      <div className="t-small mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-baseline sm:justify-between">
        <p className="text-muted-foreground">Measured per team, never per person. Teams under {k} people are hidden.</p>
        {story && <a href={`?${(() => { const u = new URLSearchParams(location.search); u.set("b", story.slug); u.delete("as"); return u; })()}`}
          onClick={e => { e.preventDefault(); window.dispatchEvent(new CustomEvent("iaw-business", { detail: story.slug })); }}
          className="underline decoration-1 underline-offset-4 hover:decoration-2">{story.text}</a>}
      </div>

      <dl data-iaw="stats" className="mt-6 grid border-y sm:grid-cols-3">
        {numbers.map(([label, value, subs], i) => (
          <div key={label} className={cn("grid grid-cols-[1fr_auto] gap-x-4 py-4 sm:block", i > 0 && "border-t sm:border-l sm:border-t-0 sm:pl-6", i < 2 && "sm:pr-6")}>
            <dt className="t-label col-start-1 text-muted-foreground">{label}</dt>
            <dd className="t-stat col-start-2 row-span-3 row-start-1 self-center text-right tabular-nums sm:mt-1 sm:text-left">{value}</dd>
            {subs.filter(Boolean).map(s => <dd key={s} className="t-label col-start-1 mt-1 font-normal text-muted-foreground">{s}</dd>)}
          </div>
        ))}
      </dl>

      {tips.length > 0 && (
        <section id="next" data-iaw="next" className="mt-10 scroll-mt-4">
          <h2 className="t-h2">What to do next</h2>
          <div className="mt-3 max-w-[66ch] space-y-2">{tips.map(t => <p key={t.text}>{t.text}</p>)}</div>
        </section>
      )}

      <nav data-iaw="questions" aria-label="Jump to an answer" className="t-small mt-10 flex flex-wrap items-baseline gap-x-5 gap-y-2">
        <span className="text-muted-foreground">Jump to</span>
        {questions.map(([q, id]) => (
          <a key={id} href={`#${id}`} onClick={e => { e.preventDefault(); jump(id); }} className="underline decoration-1 underline-offset-4 hover:decoration-2">{q}</a>
        ))}
      </nav>

      <section id="pay" data-iaw="chart" className="mt-8 scroll-mt-4 border-t pt-8">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <h2 className="t-h2">{money ? "Value of time saved and licence costs" : "Value of time saved"}, by month</h2>
          <div className="t-label flex flex-wrap gap-x-4 gap-y-1 font-normal text-muted-foreground">
            {lvl === "team" ? <>
              <span className="flex items-center gap-2"><span className="h-3 w-3 border border-accent-1" />Estimated from headcount share</span>
              <span className="flex items-center gap-2"><span className="h-3 w-3 bg-accent-1" />The team's own number</span>
            </> : money ? <>
              <span className="flex items-center gap-2"><span className="h-3 w-3 bg-accent-1 opacity-40" />Covers the licences only</span>
              <span className="flex items-center gap-2"><span className="h-3 w-3 bg-accent-1" />Gain above licences</span>
              <span className="flex items-center gap-2"><span className="w-4 border-t-2 border-dashed border-line" />Licence costs</span>
            </> : <span className="flex items-center gap-2"><span className="h-3 w-3 bg-accent-1" />Value of time saved</span>}
          </div>
        </div>
        <div className="mt-4"><MonthChart months={d.months} series="money" showCost={money} estimated={estimated} /></div>
        {payNote && <p className="t-small mt-3 text-muted-foreground">{payNote}</p>}
        {lvl === "team" && <p className="t-small mt-3 text-muted-foreground">Only {monL(d.month)} is measured for this team. Earlier months are the company's numbers times the team's share of headcount, so a change against {monL(d.month)} is not a real rise or fall.</p>}
      </section>

      <div className="mt-8 border-t">
        {!!d.tasks.length && (
          <Part id="tasks" title="Where the time is saved" note={`${hr(c.hours_saved)} h in ${monL(d.month)}`}>
            <ul>{d.tasks.slice(0, 6).map(t => <BarRow key={t.task} name={t.task} share={t.hours_saved / maxTask} value={`${hr(t.hours_saved)} h`} />)}</ul>
          </Part>
        )}

        {money && d.tools.length > 0 && (
          <Part id="licences" title="Licences" note={`${eur(c.spend_eur)} a month${waste ? ` · ${eur(waste)} unused` : ""}`}>
            <ul>
              <li className="t-label hidden grid-cols-[minmax(0,13rem)_1fr_7rem_7rem] gap-4 border-b py-2 text-muted-foreground sm:grid" aria-hidden>
                <span>Tool</span><span>Seats: filled = used</span><span className="text-right">Cost / month</span><span className="text-right">Unused</span>
              </li>
              {d.tools.map(t => {
                const u = t.seats ? Math.min(t.active_users, t.seats) : t.active_users;
                return (
                  <li key={t.tool} className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 border-b py-3 last:border-0 sm:grid-cols-[minmax(0,13rem)_1fr_7rem_7rem] sm:items-center">
                    <span className="col-start-1 row-start-1">{t.tool}</span>
                    <span className="col-span-2 col-start-1 row-start-2 sm:col-span-1 sm:col-start-2 sm:row-start-1">
                      {t.seats ? <span className="flex flex-wrap items-center gap-x-3 gap-y-1"><Seats used={u} seats={t.seats} /><span className="t-small whitespace-nowrap text-muted-foreground">{u} of {t.seats} used</span></span>
                        : <span className="t-small text-muted-foreground">{t.active_users} active, seats not set</span>}
                    </span>
                    <span className="col-start-2 row-start-1 text-right tabular-nums sm:col-start-3">{t.monthly_cost_eur ? eur(t.monthly_cost_eur) : <span className="text-muted-foreground">price not set</span>}</span>
                    <span className="t-small col-span-2 col-start-1 row-start-3 tabular-nums text-muted-foreground sm:col-span-1 sm:col-start-4 sm:row-start-1 sm:text-right sm:text-base">
                      {t.unused_seats ? <><span className="sm:hidden">{t.unused_seats} unused: </span>{eur(t.wasted_eur)}<span className="sm:hidden"> a month</span></> : <span className="sm:text-muted-foreground">–</span>}
                    </span>
                  </li>
                );
              })}
            </ul>
          </Part>
        )}

        {!!d.roles.length && (
          <Part id="teams" title="Teams" note={lvl === "team" ? `company average ${Math.round(avg * 100)}% use AI`
            : `${teamsUsing} · company average ${Math.round(avg * 100)}%`}>
            <ul>{[...d.roles].sort((a, b) => Number(!!a.hidden) - Number(!!b.hidden)).map(x => x.hidden
              ? <li key={x.role} className="grid gap-x-4 gap-y-1 border-b py-3 last:border-0 sm:grid-cols-[minmax(0,13rem)_1fr]"><span>{x.role}</span><span className="text-muted-foreground sm:text-right">under {k} people, not shown</span></li>
              : <BarRow key={x.role} wide name={x.role} share={x.adoption ?? 0} value={`${Math.round((x.adoption ?? 0) * 100)}% use AI`} sub={`· ${hr(x.hours_saved)} h`} />)}</ul>
            {nSmall === 1 && <p className="t-small mt-3 max-w-[62ch] text-muted-foreground">With one team hidden, its hours can be worked out from the {lvl === "team" ? "team" : "company"} total.</p>}
          </Part>
        )}

        {!!d.kpis?.length && (
          <Part id="kpis" title="Business numbers" note="raw counts, not adjusted for hours worked">
            <Table head={["Number", `First (${monS(d.kpis[0].first_month)})`, `Latest (${monS(d.kpis[0].last_month)})`, "Change"]} rows={d.kpis.map(k2 => { const ch = k2.first ? (k2.last - k2.first) / k2.first : 0; return [
              k2.name, k2.first.toLocaleString("en-US"), k2.last.toLocaleString("en-US"),
              <span className={ch >= 0 ? "text-accent-1" : "text-destructive"}>{ch >= 0 ? "+" : ""}{Math.round(ch * 100)}%</span>]; })} />
          </Part>
        )}

        <Fold id="calc" title="How the hours are calculated" note={calcNote}>
          <p className="max-w-[62ch]">No tool measures saved time directly. Benchmarks give minutes per AI action, for example 6 min per ChatGPT request or 15 min per Copilot day. These are starting assumptions, not measured values, and can be changed in the config. A one-question staff survey each month corrects the estimate once {k} or more people answer.</p>
          <div className="mt-6">
            <Table head={["Step", "Value"]} rows={[
              ["Hours from benchmarks", `${hr(bh)} h`],
              ["Survey correction", lvl === "team" ? "company-wide" : `× ${used ? cal.factor : 1} (${cal.n ?? 0} answers${used ? "" : `, needs ${k}`})`],
              [<span className="font-semibold">Hours saved</span>, <span className="font-semibold">{hr(c.hours_saved)} h</span>],
            ]} />
          </div>
          {cal.capped && <p className="mt-4 text-destructive">Survey and benchmarks differ by 4× or more. Check the benchmark values.</p>}
          {!!d.measurement?.evidence?.length && (() => {
            const e0 = d.measurement!.evidence![0], mo = (n?: number) => n ? ` (${n} month${n > 1 ? "s" : ""})` : "";
            return (
              <div className="mt-8">
                <Table head={["Output per 100 booked hours", `Before AI${mo(e0.months_before)}`, `After AI${mo(e0.months_after)}`, "Change"]} rows={d.measurement!.evidence!.map(e => [
                  e.name, e.before.toFixed(2), e.after.toFixed(2), <span className={e.change >= 0 ? "text-accent-1" : "text-destructive"}>{e.change >= 0 ? "+" : ""}{Math.round(e.change * 100)}%</span>])}
                  note="Adjusted for hours worked, so it can differ from the raw count under Business numbers." />
              </div>
            );
          })()}
        </Fold>

        {money && <Fold id="whatif" title="Try another hourly cost" note={`now €${avgRate.toFixed(2)} an hour`}>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <label htmlFor="rate" className="t-label text-muted-foreground">Average hourly cost (€)</label>
              <div className="mt-2 flex items-center gap-4">
                <input id="rate" type="text" inputMode="decimal" value={txt ?? avgRate.toFixed(2)} onChange={e => setTxt(e.target.value.replace(/[^0-9.,]/g, ""))} className="ctl w-28 tabular-nums" />
                <input type="range" min={10} max={150} step={1} value={r} onChange={e => setTxt(e.target.value)} className="h-11 w-full accent-[var(--accent-1)]" aria-label="Average hourly cost, slider" />
              </div>
              {txt != null && <button onClick={() => setTxt(null)} className="t-small mt-2 underline underline-offset-4">Back to €{avgRate.toFixed(2)}</button>}
            </div>
            <dl className="grid grid-cols-2 gap-4">
              <div><dt className="t-label text-muted-foreground">Value of time</dt><dd className="t-stat mt-1 tabular-nums">{eur(whatIfValue)}</dd></div>
              <div><dt className="t-label text-muted-foreground">Net benefit</dt><dd className={cn("t-stat mt-1 tabular-nums", neg(whatIfNet) && "text-destructive")}>{eur(whatIfNet)}</dd></div>
            </dl>
          </div>
        </Fold>}

        <Fold id="bymonth" title="Hours and people by month" note={lvl === "team" ? "earlier months estimated" : undefined}>
          <h3 className="t-label text-muted-foreground">Hours saved</h3>
          <div className="mt-2"><MonthChart months={d.months} series="hours" showCost={false} estimated={estimated} /></div>
          <h3 className="t-label mt-8 text-muted-foreground">People using AI</h3>
          <div className="mt-2"><MonthChart months={d.months} series="people" showCost={false} estimated={estimated} /></div>
        </Fold>
      </div>

      <p className="t-label mt-8 font-normal text-muted-foreground">{REPORT ? "Report for this role only · numbers are estimates" : d.real ? "Your data · read on this computer · numbers are estimates" : "Demo · fictional business · simulated data"}</p>
    </div>
  );
}

const ORDER = ["odoo", "m365_copilot_csv", "usage_csv", "people_csv", "kpi_csv", "licences", "survey_csv", "personio", "github_copilot", "claude_code_local", "anthropic_admin"];

function Sources() {
  const [list, setList] = React.useState<Connector[]>([]);
  React.useEffect(() => { fetch("data/connectors.json").then(r => r.json()).then(setList).catch(() => {}); }, []);
  const demo = list.length > 0 && list.every(c => !c.enabled && !c.last);
  const rank = (c: Connector) => { const i = ORDER.indexOf(c.key); return i < 0 ? 99 : i; };
  const tested = (c: Connector) => c.status === "tested" ? "Tested" : "From vendor docs";
  return (
    <div>
      <h1 className="t-h1">Where the numbers come from</h1>
      <p className="mt-4 max-w-[62ch] text-muted-foreground">Every source is optional. Turn one on in <code className="bg-muted px-1">isaiworthit.config.json</code>, then run <code className="bg-muted px-1">python3 isaiworthit.py sync</code>.</p>
      <p className="t-small mt-3 max-w-[62ch] text-muted-foreground"><span className="font-medium text-foreground">Tested</span> means run end to end against a local Odoo 18 or real export files. <span className="font-medium text-foreground">From vendor docs</span> means built from the vendor's API documentation, not yet run against a live account.</p>
      {(["company", "ai"] as const).map(kind => (
        <section key={kind} className="mt-12">
          <h2 className="t-h2">{kind === "ai" ? "AI tool usage" : "Company data"}</h2>
          <div className="mt-4">
            <Table left={[0, 1]} fixed={["28%", "54%", "18%"]} head={["Source", "Gives, and how", demo ? "Status" : "Rows read"]} rows={list.filter(c => c.kind === kind).sort((a, b) => rank(a) - rank(b)).map(c => [
              <><div className="font-medium">{c.label}</div>{!demo && <div className="t-label font-normal text-muted-foreground">{tested(c)}</div>}</>,
              <><div>{c.provides}</div><div className="t-small mt-1 text-muted-foreground">{c.how}</div></>,
              <span className="whitespace-nowrap">{demo ? <span className={c.status === "tested" ? "" : "text-muted-foreground"}>{tested(c)}</span>
                : c.last ? (c.last.ok
                  ? <span title={c.last.at ? `Last sync ${c.last.at.replace("T", " ")}` : undefined}>{c.last.rows} rows{c.sample && <span className="t-label block font-normal text-muted-foreground">sample file</span>}</span>
                  : <span className="text-destructive" title={c.last.message}>Error</span>) : c.enabled ? "On, not synced" : <span className="text-muted-foreground">Off</span>}</span>])} />
          </div>
        </section>))}
    </div>
  );
}

function Odoo() {
  const shots: [string, string, string][] = [
    ["img/odoo-months.jpg", "One row per month", "The IsAIWorthIt app in Odoo 18: one row per month with people using AI, hours saved, value of time saved, licence costs and net benefit"],
    ["img/odoo-teams.jpg", "Hours saved per department, as an Odoo pivot (filtered to one tool)", "Odoo pivot view filtered to ChatGPT Team: hours saved per department and month, with small departments combined into one row"],
  ];
  return (
    <div>
      <h1 className="t-h1">Also runs inside Odoo 18</h1>
      <p className="mt-4 max-w-[62ch] text-muted-foreground">The same measurement as a native Odoo app, for companies that already run on Odoo. It reads departments from the Employees app and keeps the results next to them.</p>
      <ul className="mt-6 max-w-[66ch] space-y-3 border-l-2 border-accent-1 pl-5">
        <li><span className="font-medium">Its own Odoo app,</span> built for Odoo 18 and tested on Community. It only needs the Employees app. Usage is imported from a CSV export of Microsoft 365, GitHub Copilot, ChatGPT Team or a shared sheet.</li>
        <li><span className="font-medium">Two access groups.</span> Viewer sees hours per team. Manager also sees money, licences and the import.</li>
        <li><span className="font-medium">Departments under 5 people are combined</span> into one row (“Small teams (combined)” below). Users are matched to employees by work e-mail only to find their department; nothing is stored per person.</li>
      </ul>
      <p className="t-small mt-10 max-w-[66ch] text-muted-foreground">Screenshots from a local Odoo 18 Community with test data for the fictional Rheinmark Handels GmbH, not the demo businesses on the overview, so the numbers differ. Some test department names are German. The module ships with automated tests for Odoo's test runner.</p>
      {shots.map(([src, title, alt]) => (
        <figure key={src} className="mt-8">
          <h2 className="t-h2">{title}</h2>
          <a href={src} target="_blank" rel="noopener" className="mt-4 block"><img src={src} alt={alt} loading="lazy" className="block w-full border" /></a>
          <a href={src} target="_blank" rel="noopener" className="t-small mt-2 inline-block underline underline-offset-4 sm:hidden">Open full size</a>
        </figure>
      ))}
    </div>
  );
}

function Access({ base }: { base: Business | null }) {
  const k = base?.k_min ?? 5;
  const ev = base && !REPORT ? scoped(base, "everyone") : null;
  return (
    <div>
      <h1 className="t-h1">Who sees what</h1>
      <p className="mt-4 max-w-[62ch] text-muted-foreground">Each reader gets their own report file. What they may not see is removed before the file is made, not just hidden.</p>
      <div className="mt-8">
        <Matrix cols={["Management", "Team lead", "Everyone", "You"]} widths={["30%", "16%", "18%", "14%", "22%"]} rows={[
          ["Company totals", "yes", "averages", "yes", "yes"],
          [`Teams (${k}+ people)`, "all", "own + sub-teams", "–", "–"],
          ["Value of time saved (€)", "yes", "own team", "yes", "–"],
          ["Average hourly cost (€)", "yes", "–", "–", "–"],
          ["Costs, licences, business numbers", "yes", "–", "–", "–"],
          ["Single people", "never", "never", "never", "only you, on your computer"],
        ]} />
      </div>

      {base && ev && (
        <section className="mt-14" data-iaw="readers">
          <h2 className="t-h2">One month, two readers: {base.name}{base.real ? "" : " (fictional)"}</h2>
          <p className="t-small mt-2 max-w-[62ch] text-muted-foreground">The same {monL(base.month)} data, as Management and as every employee sees it. Switch with “View as” on the overview.</p>
          <div className="mt-6">
            <Matrix cols={["Management", "Everyone"]} widths={["22%", "50%", "28%"]} rows={[
              ["Headline", `${eur(base.current.value_eur)} saved − ${eur(base.current.spend_eur)} licences = ${eur(base.current.net_eur)}`, `${hr(ev.current.hours_saved)} hours saved`],
              ["People using AI", `${base.current.active_users} / ${base.opted_in}`, `${ev.current.active_users} / ${ev.opted_in}`],
              ["Teams", base.roles.filter(x => !x.hidden).map(x => `${x.role} ${Math.round((x.adoption ?? 0) * 100)}%`).join(", ") || "–", "removed"],
              ["Licences and costs", base.tools.map(t => t.seats ? `${t.tool}: ${Math.min(t.active_users, t.seats)} of ${t.seats} seats` : t.tool).join(", ") || "–", "removed"],
              ["Business numbers", base.kpis?.length ? base.kpis.map(x => `${x.name} ${x.first} → ${x.last}`).join(", ") : "–", "removed"],
            ]} />
          </div>
        </section>
      )}

      <p className="mt-10 max-w-[62ch] text-muted-foreground">Report files: <code className="bg-muted px-1">python3 isaiworthit.py reports</code>. Nothing is uploaded, prompt text is never stored, and names become codes. Designed with {`§${NB}87(1)${NB}No.${NB}6${NB}BetrVG`} and the EU{NB}AI{NB}Act in mind. Not legal advice; check with your works council.</p>
    </div>
  );
}

const STORY: Record<string, { slug: string; text: string }> = {
  loss: { slug: "hotel", text: "See a business where AI does not pay off yet →" },
  win: { slug: "tax-office", text: "See one where it does →" },
};

const PAGES = ["odoo", "sources", "access"];
const REPO = "https://github.com/samaistudio/IsAIWorthIt";

export default function App() {
  // ?page=odoo|sources|access opens that tab directly (links from the portfolio and the README)
  const [page, setPageState] = React.useState(() => { const p = params.get("page") ?? ""; return PAGES.includes(p) && !(REPORT && p !== "access") ? p : "overview"; });
  const setPage = (v: string) => {
    setPageState(v);
    const u = new URL(location.href);
    if (v === "overview") u.searchParams.delete("page"); else u.searchParams.set("page", v);
    history.replaceState(null, "", u);
  };
  const [list, setList] = React.useState<{ slug: string; name: string }[]>([]);
  const [slug, setSlug] = React.useState(params.get("b") ?? "");
  const [base, setBase] = React.useState<Business | null>(REPORT);
  const [role, setRole] = React.useState(params.get("as") ?? "management");
  const [preview, setPreview] = React.useState(false);

  React.useEffect(() => {
    if (REPORT) return;
    (async () => {
      const demo = await fetch("data/businesses/index.json").then(r => r.json());
      // your own company (created by `python3 isaiworthit.py sync`) stays local; it is listed last, the demo opens first
      const mine = await fetch("data/businesses/your-company.json").then(r => r.ok ? r.json() : null).catch(() => null);
      const l = mine ? [...demo, { slug: "your-company", name: `Your data: ${mine.name}` }] : demo;
      setList(l); setSlug(s => s || l[0]?.slug);
    })();
  }, []);
  React.useEffect(() => { if (REPORT || !slug) return; fetch(`data/businesses/${slug}.json`).then(r => r.json()).then(setBase); const u = new URL(location.href); u.searchParams.set("b", slug); history.replaceState(null, "", u); }, [slug]);
  React.useEffect(() => {
    const go = (e: Event) => { setSlug((e as CustomEvent).detail); setRole("management"); setPage("overview"); };
    window.addEventListener("iaw-business", go);
    return () => window.removeEventListener("iaw-business", go);
  }, []);
  // #licences, #teams, #tasks, #pay, #calc, #next open and mark that part (also usable from the portfolio)
  React.useEffect(() => {
    const h = location.hash.slice(1);
    if (base && h && !["dark", "light"].includes(h)) setTimeout(() => jump(h), 300);
  }, [base]);

  const roles = (base?.roles ?? []).filter(r => !r.hidden);
  const effRole = roles.some(r => "team:" + r.role === role) || role === "everyone" ? role : "management";
  const data = base ? (REPORT ? base : scoped(base, effRole)) : null;
  const kind = effRole.startsWith("team:") ? "team" : effRole;
  const pages: [string, string, string][] = [["overview", "Overview", "Overview"], ...(REPORT ? [] : [["odoo", "Inside Odoo", "Odoo"], ["sources", "Data sources", "Sources"]] as [string, string, string][]), ["access", "Who sees what", "Who sees what"]];
  const story = !REPORT && base && !base.real && effRole === "management"
    ? (neg(base.current.net_eur) ? STORY.win : STORY.loss) : null;
  const storyOk = story && list.some(b => b.slug === story.slug) && story.slug !== slug ? story : null;

  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-8 px-4 sm:px-6 lg:px-8">
          <span className="flex h-14 items-center gap-4">
            {FROM_PORTFOLIO && <a href="../" className="t-small wordlink text-muted-foreground">← Portfolio</a>}
            <span className="font-semibold">IsAIWorthIt</span>
          </span>
          <nav className="-mx-2 flex sm:-mx-3" aria-label="Pages">
            {pages.map(([v, label, short]) => (
              <button key={v} onClick={() => setPage(v)} aria-current={page === v ? "page" : undefined}
                className={cn("t-small wordlink flex h-11 items-center whitespace-nowrap px-2 sm:h-14 sm:px-3", page === v ? "text-foreground underline decoration-current decoration-2" : "text-muted-foreground")}>
                <span className="sm:hidden">{short}</span><span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        {!REPORT && page === "overview" && (
          <p className="t-small mb-6 max-w-[70ch] text-muted-foreground">
            IsAIWorthIt shows what AI tools save a company and what the licences cost. {base?.real ? "" : "Demo with fictional businesses and simulated data. "}Built by Sam Zeidi · <a href={REPO} target="_blank" rel="noopener" className="underline underline-offset-4 hover:text-foreground">Source on GitHub</a>
          </p>
        )}
        {page === "overview" && <>
          {!REPORT && (
            <div className="mb-8" data-iaw="controls">
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                <>
                  <Select value={slug} onChange={e => { setSlug(e.target.value); setRole("management"); setPreview(false); }} aria-label="Business">{list.map(b => <option key={b.slug} value={b.slug}>{b.name}</option>)}</Select>
                  <div className="flex items-center gap-3">
                    <span className="t-small hidden text-muted-foreground lg:inline">View as</span>
                    <div role="radiogroup" aria-label="View as" data-iaw="roles" className="flex w-full sm:w-auto">
                      {([["management", "Management"], ["team", "Team lead"], ["everyone", "Everyone"]] as const).map(([v, label], i) => {
                        const on = kind === v, off = v === "team" && !roles.length;
                        return (
                          <button key={v} role="radio" aria-checked={on} disabled={off}
                            onClick={() => { setRole(v === "team" ? "team:" + roles[0].role : v); setPreview(false); }}
                            className={cn("ctl relative flex-1 whitespace-nowrap px-3 sm:flex-none", i > 0 && "-ml-px", on ? "z-10 border-foreground bg-muted font-semibold" : "text-muted-foreground", off && "cursor-not-allowed opacity-50")}>{label}</button>
                        );
                      })}
                    </div>
                  </div>
                </>
                {data && <div className="sm:ml-auto"><ExportMenu data={data} onPreview={() => setPreview(true)} /></div>}
              </div>
              {!REPORT && kind === "team" && (
                <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
                  {roles.length > 1 && (
                    <Select value={effRole} onChange={e => setRole(e.target.value)} aria-label="Team" className="shrink-0 sm:max-w-[13rem]">
                      {roles.map(r => <option key={r.role} value={"team:" + r.role}>Team: {r.role}</option>)}
                    </Select>
                  )}
                  <p className="t-small max-w-[70ch] text-muted-foreground">This is what the {effRole.slice(5)} lead sees. Costs, licences, business numbers, the task list and other teams are removed from this view, not just hidden.</p>
                </div>
              )}
              {!REPORT && kind === "everyone" && (
                <p className="t-small mt-3 max-w-[70ch] text-muted-foreground">This is what every employee sees. Costs, licences, business numbers and single teams are removed from this view, not just hidden.</p>
              )}
            </div>
          )}
          {preview && data && <Preview data={data} onClose={() => setPreview(false)} />}
          {data ? <Overview d={data} story={storyOk} aside={REPORT ? <ExportMenu data={data} onPreview={() => setPreview(true)} /> : undefined} />
            : <p className="text-muted-foreground">Loading…</p>}
        </>}
        {page === "odoo" && <Odoo />}
        {page === "sources" && <Sources />}
        {page === "access" && <Access base={base} />}
      </main>
      <footer className="border-t">
        <div className="t-small mx-auto flex max-w-5xl flex-wrap gap-x-6 gap-y-2 px-4 py-6 text-muted-foreground sm:px-6 lg:px-8">
          <span>IsAIWorthIt{base?.real ? "" : " · Built by Sam Zeidi"}</span>
          <a href={REPO} target="_blank" rel="noopener" className="underline underline-offset-4 hover:text-foreground">Source on GitHub</a>
          {!base?.real && <a href="mailto:contact.samzeidi@gmail.com" className="underline underline-offset-4 hover:text-foreground">contact.samzeidi@gmail.com</a>}
        </div>
      </footer>
    </div>
  );
}
