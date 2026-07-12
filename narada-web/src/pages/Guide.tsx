import Header from "../components/Header";

// Public user guide — how to run your marketing team. No auth required.
export default function Guide() {
  return (
    <div className="page">
      <Header />
      <main className="dashboard guide">
        <p className="eyebrow">User guide</p>
        <h2>
          How to run your <span className="accent">marketing team</span>
        </h2>
        <p className="muted">
          Five minutes from signup to your first published post. No marketing
          experience needed — that's the point.
        </p>

        <div className="card">
          <h3>1 · Onboard your business (~2 minutes)</h3>
          <ul>
            <li>Click <strong>Get started</strong> and create your account.</li>
            <li>
              Enter your <strong>business name</strong> and{" "}
              <strong>website URL</strong> — that's all that's required.
            </li>
            <li>
              Optional but recommended: logo, product images, and up to 3 PDFs
              (brochure, pitch deck, menu) — the more you share, the sharper
              your brief.
            </li>
            <li>
              Submit and watch: three agents study your website, research your
              market and competitors, and read your materials. This takes a
              few minutes — the page updates by itself.
            </li>
          </ul>
        </div>

        <div className="card">
          <h3>2 · Approve your Brand Brief</h3>
          <ul>
            <li>
              You'll see what the agents learned: your offering, audience,
              tone of voice, competitors, brand colors, and ready-to-use
              campaign ideas.
            </li>
            <li>
              <strong>Every field is editable</strong> — fix anything they got
              wrong. Open "Brand context" to see the full research.
            </li>
            <li>
              Click <strong>✅ That's us</strong> when it looks right. This
              becomes your team's permanent memory.
            </li>
          </ul>
        </div>

        <div className="card">
          <h3>3 · Meet your team on Telegram</h3>
          <ul>
            <li>
              Tap the <strong>Telegram button</strong> — it opens a chat with
              Narada and links it to your business automatically (just press
              START).
            </li>
            <li>
              From now on, your marketing team lives in that chat. Talk to it
              like a colleague — no commands to memorize.
            </li>
          </ul>
        </div>

        <div className="card">
          <h3>4 · Give it work — in plain language</h3>
          <p className="muted">Things people actually say:</p>
          <ul>
            <li>"Write a LinkedIn post about our new service."</li>
            <li>"Draft this week's Instagram content — 3 posts."</li>
            <li>"Research what our competitors posted this month."</li>
            <li>"Make a banner image for the Diwali offer."</li>
            <li>"How did we do this week? Give me a voice briefing."</li>
          </ul>
          <p>
            <strong>Nothing publishes without your OK.</strong> Narada always
            shows you the final copy and asks "Ship it?" first. Reply{" "}
            <em>ship it</em> to publish, or tell it what to change.
          </p>
        </div>

        <div className="card">
          <h3>5 · Watch the work happen</h3>
          <ul>
            <li>
              The <a href="#/dashboard">Dashboard</a> shows every task your
              agents complete — live, with timestamps.
            </li>
            <li>
              Your team learns: results and lessons feed back into its memory,
              so month three is sharper than day one.
            </li>
          </ul>
        </div>

        <div className="card">
          <h3>Useful chat commands</h3>
          <ul>
            <li>
              <code>/new</code> — start a fresh conversation (your business
              memory is kept; only the chat thread resets)
            </li>
            <li>
              <code>/start &lt;token&gt;</code> — re-link your business. Your token
              lives on <a href="#/telegram">the Telegram page</a> of this web
              app — sign in and open it anytime; the one-tap connect button
              is there too
            </li>
            <li>
              <code>/stop</code> — cancel a running task
            </li>
          </ul>
        </div>

        <div className="card notice">
          <h3>Tips for great results</h3>
          <ul>
            <li>
              <strong>Be specific about the goal</strong>: "a post that gets
              signups for the webinar" beats "a post".
            </li>
            <li>
              <strong>Correct it once, it remembers</strong>: say "never use
              emojis in our posts" and it becomes a brand rule.
            </li>
            <li>
              <strong>Ask for options</strong>: "give me 3 angles first" —
              then pick one to develop.
            </li>
          </ul>
          <a href="#/start" className="btn-primary big">
            Get started free
          </a>
        </div>
      </main>
    </div>
  );
}
