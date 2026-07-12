import { useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import Header from "../components/Header";
import { navigate } from "../config";

const splitCommas = (value: string): string[] =>
  value.split(",").map((part) => part.trim()).filter(Boolean);

const splitLines = (value: string): string[] =>
  value.split("\n").map((line) => line.trim()).filter(Boolean);

/* ---------- tiny markdown-ish renderer for context_md ----------
   ponytail: headers/bold/code/lists via regex, tables as <pre>.
   Swap for a real md lib only if the agent starts emitting more. */

const inlineMd = (text: string): ReactNode[] =>
  text
    .split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
    .filter(Boolean)
    .map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**"))
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      if (part.startsWith("`") && part.endsWith("`"))
        return <code key={i}>{part.slice(1, -1)}</code>;
      return part;
    });

function ContextMd({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  let table: string[] = [];
  const flushList = () => {
    if (!list.length) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`}>
        {list.map((item, i) => (
          <li key={i}>{inlineMd(item)}</li>
        ))}
      </ul>,
    );
    list = [];
  };
  const flushTable = () => {
    if (!table.length) return;
    blocks.push(<pre key={`tb-${blocks.length}`}>{table.join("\n")}</pre>);
    table = [];
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushList();
      flushTable();
      blocks.push(<h4 key={`h-${blocks.length}`}>{inlineMd(heading[2])}</h4>);
      continue;
    }
    if (/^(?:[-*+]|\d+\.)\s+/.test(line)) {
      flushTable();
      list.push(line.replace(/^(?:[-*+]|\d+\.)\s+/, ""));
      continue;
    }
    if (line.startsWith("|")) {
      flushList();
      table.push(line);
      continue;
    }
    flushList();
    flushTable();
    if (line) blocks.push(<p key={`p-${blocks.length}`}>{inlineMd(line)}</p>);
  }
  flushList();
  flushTable();
  return <div className="context-md">{blocks}</div>;
}

function Chips({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="chip-row" aria-hidden="true">
      {items.map((item, i) => (
        <span className="chip" key={`${item}-${i}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

export default function Brief() {
  const data = useQuery(api.briefs.getMine);
  const update = useMutation(api.briefs.update);
  const approve = useMutation(api.briefs.approve);

  // Local editable copies; saved on blur.
  const [offering, setOffering] = useState("");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("");
  const [competitors, setCompetitors] = useState("");
  const [colors, setColors] = useState("");
  const [ideas, setIdeas] = useState("");
  const [contextMd, setContextMd] = useState("");
  const [editingContext, setEditingContext] = useState(false);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const brief = data?.brief;
  // Keyed on id AND status so the form re-syncs when the crew flips the
  // brief from analyzing → ready (fields arrive with the status change).
  const briefKey = brief ? `${brief._id}:${brief.status}` : null;

  useEffect(() => {
    if (brief && briefKey && briefKey !== loadedKey) {
      setOffering(brief.offering ?? "");
      setAudience(brief.audience ?? "");
      setTone((brief.tone ?? []).join(", "));
      setCompetitors((brief.competitors ?? []).join(", "));
      setColors((brief.colors ?? []).join(", "));
      setIdeas((brief.campaign_ideas ?? []).join("\n"));
      setContextMd(brief.context_md ?? "");
      setLoadedKey(briefKey);
    }
  }, [brief, briefKey, loadedKey]);

  if (data === undefined) {
    return (
      <div className="page center">
        <div className="spinner" />
      </div>
    );
  }
  if (data === null || !brief) {
    return (
      <div className="page">
        <Header />
        <div className="card notice">
          <h2>No brief yet</h2>
          <p>
            <a href="#/start">Start onboarding</a> to get one.
          </p>
        </div>
      </div>
    );
  }

  const payload = () => ({
    brief_id: brief._id,
    offering,
    audience,
    tone: splitCommas(tone),
    competitors: splitCommas(competitors),
    colors: splitCommas(colors),
    campaign_ideas: splitLines(ideas),
    context_md: contextMd,
  });

  const save = () => void update(payload());

  const approveBrief = async () => {
    setBusy(true);
    try {
      await update(payload());
      await approve({ brief_id: brief._id });
      navigate("/telegram");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <Header />
      <div className="card form-card wide">
        <h2>
          Brand brief · <span className="accent">{data.business.name}</span>
        </h2>
        <p className="muted">
          Everything below is editable — fix anything we got wrong, then
          approve.
        </p>

        <label>
          What you offer
          <textarea
            value={offering}
            onChange={(e) => setOffering(e.target.value)}
            onBlur={save}
            rows={3}
          />
        </label>
        <label>
          Who it's for
          <textarea
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            onBlur={save}
            rows={3}
          />
        </label>
        <label>
          Tone <span className="muted">(comma-separated adjectives)</span>
          <input value={tone} onChange={(e) => setTone(e.target.value)} onBlur={save} />
        </label>
        <Chips items={splitCommas(tone)} />
        <label>
          Competitors <span className="muted">(comma-separated)</span>
          <input
            value={competitors}
            onChange={(e) => setCompetitors(e.target.value)}
            onBlur={save}
          />
        </label>
        <Chips items={splitCommas(competitors)} />
        <label>
          Brand colors <span className="muted">(comma-separated hex)</span>
          <input value={colors} onChange={(e) => setColors(e.target.value)} onBlur={save} />
        </label>
        <div className="swatches">
          {splitCommas(colors).map((color) => (
            <span
              key={color}
              className="swatch"
              style={{ background: color }}
              title={color}
            />
          ))}
        </div>
        <label>
          Campaign ideas <span className="muted">(one per line)</span>
          <textarea
            value={ideas}
            onChange={(e) => setIdeas(e.target.value)}
            onBlur={save}
            rows={6}
          />
        </label>

        {contextMd.trim().length > 0 && (
          <details className="context-details">
            <summary>Brand context (what Narada learned)</summary>
            <div className="context-body">
              <button
                type="button"
                className="btn-ghost context-edit-toggle"
                onClick={() => setEditingContext((v) => !v)}
              >
                {editingContext ? "Done editing" : "Edit"}
              </button>
              {editingContext ? (
                <textarea
                  className="context-editor"
                  value={contextMd}
                  onChange={(e) => setContextMd(e.target.value)}
                  onBlur={save}
                  rows={16}
                  aria-label="Brand context markdown"
                />
              ) : (
                <ContextMd text={contextMd} />
              )}
            </div>
          </details>
        )}

        {brief.status === "approved" ? (
          <p className="muted">
            Approved ✓ — <a href="#/telegram">meet your team on Telegram</a>
          </p>
        ) : (
          <button
            className="btn-primary big"
            onClick={() => void approveBrief()}
            disabled={busy}
          >
            ✅ That's us
          </button>
        )}
      </div>
    </div>
  );
}
