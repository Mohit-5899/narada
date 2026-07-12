import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import type { Id } from "../../convex/_generated/dataModel";
import Header from "../components/Header";
import { navigate } from "../config";

export default function Start() {
  const data = useQuery(api.briefs.getMine);

  useEffect(() => {
    if (data?.brief.status === "ready") navigate("/brief");
    if (data?.brief.status === "approved") navigate("/telegram");
  }, [data?.brief.status]);

  if (data === undefined) {
    return (
      <div className="page center">
        <div className="spinner" />
      </div>
    );
  }
  if (data === null) return <OnboardingForm />;
  return <Analyzing briefId={data.brief._id} businessName={data.business.name} />;
}

const MAX_IMAGES = 5;

function OnboardingForm() {
  const generateUploadUrl = useMutation(api.businesses.generateUploadUrl);
  const create = useMutation(api.businesses.create);

  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  const [oneLiner, setOneLiner] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const [images, setImages] = useState<File[]>([]);
  const [pdfs, setPdfs] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const upload = async (file: File): Promise<Id<"_storage">> => {
    const postUrl = await generateUploadUrl();
    const result = await fetch(postUrl, {
      method: "POST",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!result.ok) throw new Error(`Upload failed (${result.status})`);
    const { storageId } = await result.json();
    return storageId;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !website.trim()) {
      setError("Business name and website are required.");
      return;
    }
    const url = /^https?:\/\//i.test(website.trim())
      ? website.trim()
      : `https://${website.trim()}`;
    setBusy(true);
    setError(null);
    try {
      const logo_id = logo ? await upload(logo) : undefined;
      const image_ids = await Promise.all(images.map(upload));
      const pdf_ids = await Promise.all(pdfs.map(upload));
      await create({
        name: name.trim(),
        website: url,
        one_liner: oneLiner.trim() || undefined,
        logo_id,
        image_ids,
        pdf_ids: pdf_ids.length ? pdf_ids : undefined,
      });
      // getMine goes non-null reactively → Start flips to <Analyzing/>.
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <Header />
      <div className="card form-card">
        <h2>Tell Narada about your business</h2>
        <p className="muted">
          30 seconds of you, then ~90 seconds of our agents.
        </p>
        <form onSubmit={submit}>
          <label>
            Business name *
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Hoichoi"
              required
            />
          </label>
          <label>
            Website URL *
            <input
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="hoichoi.tv"
              required
            />
          </label>
          <label>
            What do you sell? <span className="muted">(optional, one line)</span>
            <input
              value={oneLiner}
              onChange={(e) => setOneLiner(e.target.value)}
              placeholder="Bengali OTT streaming"
            />
          </label>
          <label>
            Logo <span className="muted">(optional)</span>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setLogo(e.target.files?.[0] ?? null)}
            />
          </label>
          <label>
            Product / brand images{" "}
            <span className="muted">(optional, up to {MAX_IMAGES})</span>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) =>
                setImages(Array.from(e.target.files ?? []).slice(0, MAX_IMAGES))
              }
            />
          </label>
          <label>
            Brochures / decks <span className="muted">(optional PDFs, up to 3)</span>
            <input
              type="file"
              accept="application/pdf"
              multiple
              onChange={(e) =>
                setPdfs(Array.from(e.target.files ?? []).slice(0, 3))
              }
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="btn-primary big" type="submit" disabled={busy}>
            {busy ? "Uploading…" : "Build my brand brief"}
          </button>
        </form>
      </div>
    </div>
  );
}

const AGENTS = [
  {
    name: "Site Analyst",
    lines: [
      "Fetching your homepage…",
      "Reading about + pricing pages…",
      "Extracting your offering and copy…",
    ],
  },
  {
    name: "Market Researcher",
    lines: [
      "Searching your market…",
      "Scanning competitors…",
      "Sizing your audience…",
    ],
  },
  {
    name: "Brand Analyst",
    lines: [
      "Sampling brand colors…",
      "Distilling tone of voice…",
      "Drafting five campaign ideas…",
    ],
  },
];

function Analyzing({
  briefId,
  businessName,
}: {
  briefId: Id<"brand_briefs">;
  businessName: string;
}) {
  const devSeed = useMutation(api.briefs.devSeed);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="page">
      <Header />
      <div className="analyzing">
        <h2>
          Analyzing <span className="accent">{businessName}</span>…
        </h2>
        <div className="agent-grid">
          {AGENTS.map((agent, i) => (
            <div className="card agent-card" key={agent.name}>
              <div className="spinner small" />
              <h3>{agent.name}</h3>
              <p className="muted">
                {agent.lines[(tick + i) % agent.lines.length]}
              </p>
            </div>
          ))}
        </div>
        <p className="muted">
          Live status — this page flips the moment the crew reports back.
        </p>
        {tick >= 4 && (
          <button className="btn-ghost" onClick={() => void devSeed({ brief_id: briefId })}>
            Taking long? Load a sample brief (demo)
          </button>
        )}
      </div>
    </div>
  );
}
