import Header from "../components/Header";

const STEPS = [
  {
    title: "Onboard",
    body: "Give us your name, your website, and 30 seconds. The crew reads your site, your market, and your brand.",
  },
  {
    title: "Meet your crew",
    body: "A brand brief lands in ~90 seconds. Edit anything, approve it, and your agents are briefed for good.",
  },
  {
    title: "Watch it publish",
    body: "Say “launch a campaign” on Telegram. Real posts go out; every task, trace, and dollar shows on your dashboard.",
  },
];

const GANAS = [
  {
    glyph: "◈",
    name: "Researcher",
    line: "Reads your market and competitors so every campaign starts informed.",
  },
  {
    glyph: "✎",
    name: "Copywriter",
    line: "Writes in your voice — posts, emails, hooks — from the approved brief.",
  },
  {
    glyph: "➤",
    name: "Publisher",
    line: "Ships to real surfaces: LinkedIn, email, Telegram. No sandbox theatre.",
  },
  {
    glyph: "∿",
    name: "Analyst",
    line: "Watches what lands, reports what worked, and feeds it back to the crew.",
  },
];

export default function Landing() {
  return (
    <div className="page">
      <Header />

      <main>
        {/* hero */}
        <section className="hero">
          <p className="eyebrow">AI Marketing Agency</p>
          <h1>
            Every business has a story.
            <br />
            <span className="accent">Narada</span> makes the three worlds hear it.
          </h1>
          <p className="pitch">
            A manager agent and his ganas study your business, write your brand
            brief, and run real campaigns — while you watch every task, trace,
            and dollar in one dashboard. You approve; the three worlds hear.
          </p>
          <div className="hero-ctas">
            <a href="#/start" className="btn-primary big">
              Get started
            </a>
            <a href="#/dashboard" className="btn-ghost">
              See the dashboard
            </a>
          </div>
          <p className="hero-sub">Brand brief in ~90 seconds. No credit card.</p>
        </section>

        {/* how it works */}
        <section className="section" aria-labelledby="how-title">
          <p className="eyebrow">How it works</p>
          <h2 id="how-title">From URL to live campaign</h2>
          <div className="steps">
            {STEPS.map((step, i) => (
              <div className="step" key={step.title}>
                <span className="step-num" aria-hidden="true">
                  {i + 1}
                </span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* the crew */}
        <section className="section" aria-labelledby="crew-title">
          <p className="eyebrow">The crew</p>
          <h2 id="crew-title">One messenger, four ganas</h2>
          <p className="lead">
            Named for the divine messenger who carried news between the worlds
            — Narada manages, the ganas execute.
          </p>
          <div className="crew-lead">
            <span className="crew-glyph" aria-hidden="true">
              ✦
            </span>
            <span className="crew-role">Manager</span>
            <h3>Narada</h3>
            <p>
              Takes your word on Telegram, plans the campaign, briefs the
              ganas, and answers for every result.
            </p>
          </div>
          <div className="crew-grid">
            {GANAS.map((gana) => (
              <div className="crew-card" key={gana.name}>
                <span className="crew-glyph" aria-hidden="true">
                  {gana.glyph}
                </span>
                <h3>{gana.name}</h3>
                <p>{gana.line}</p>
              </div>
            ))}
          </div>
        </section>

        {/* live proof */}
        <section className="section" aria-labelledby="proof-title">
          <p className="eyebrow">Real surfaces</p>
          <h2 id="proof-title">Published where it counts</h2>
          <div className="proof">
            <span className="proof-chip">LinkedIn posts</span>
            <span className="proof-chip">Email campaigns</span>
            <span className="proof-chip">Telegram command center</span>
            <span className="proof-chip">Live dashboard + traces</span>
          </div>
        </section>

        {/* pricing */}
        <section className="section" aria-labelledby="pricing-title">
          <p className="eyebrow">Pricing</p>
          <h2 id="pricing-title">One plan, whole agency</h2>
          <div className="pricing">
            <div className="card price-card">
              <h3>Narada Hosted</h3>
              <div className="price">
                $9<span>/mo</span>
              </div>
              <ul>
                <li>Full agent crew, managed for you</li>
                <li>Brand brief in ~90 seconds</li>
                <li>Real publishing: LinkedIn · email · Telegram</li>
                <li>Live campaign dashboard + traces</li>
              </ul>
              <a href="#/checkout" className="btn-primary">
                Subscribe
              </a>
            </div>
          </div>
        </section>
      </main>

      <div className="divider" aria-hidden="true">
        ✦
      </div>
      <footer className="footer">
        <p className="tagline">
          &ldquo;Every business has a story. Narada makes the three worlds hear
          it.&rdquo;
        </p>
        Built on Hermes for the GrowthX Buildathon.
      </footer>
    </div>
  );
}
