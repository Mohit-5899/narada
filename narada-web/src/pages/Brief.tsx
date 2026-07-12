import { useEffect, useState } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import Header from "../components/Header";
import { navigate } from "../config";

const splitCommas = (value: string): string[] =>
  value.split(",").map((part) => part.trim()).filter(Boolean);

const splitLines = (value: string): string[] =>
  value.split("\n").map((line) => line.trim()).filter(Boolean);

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
  const [loadedId, setLoadedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const brief = data?.brief;

  useEffect(() => {
    if (brief && brief._id !== loadedId) {
      setOffering(brief.offering ?? "");
      setAudience(brief.audience ?? "");
      setTone((brief.tone ?? []).join(", "));
      setCompetitors((brief.competitors ?? []).join(", "));
      setColors((brief.colors ?? []).join(", "));
      setIdeas((brief.campaign_ideas ?? []).join("\n"));
      setLoadedId(brief._id);
    }
  }, [brief, loadedId]);

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

  const save = () =>
    void update({
      brief_id: brief._id,
      offering,
      audience,
      tone: splitCommas(tone),
      competitors: splitCommas(competitors),
      colors: splitCommas(colors),
      campaign_ideas: splitLines(ideas),
    });

  const approveBrief = async () => {
    setBusy(true);
    try {
      await update({
        brief_id: brief._id,
        offering,
        audience,
        tone: splitCommas(tone),
        competitors: splitCommas(competitors),
        colors: splitCommas(colors),
        campaign_ideas: splitLines(ideas),
      });
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
            rows={2}
          />
        </label>
        <label>
          Who it's for
          <textarea
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            onBlur={save}
            rows={2}
          />
        </label>
        <label>
          Tone <span className="muted">(comma-separated adjectives)</span>
          <input value={tone} onChange={(e) => setTone(e.target.value)} onBlur={save} />
        </label>
        <label>
          Competitors <span className="muted">(comma-separated)</span>
          <input
            value={competitors}
            onChange={(e) => setCompetitors(e.target.value)}
            onBlur={save}
          />
        </label>
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
