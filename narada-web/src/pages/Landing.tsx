import Header from "../components/Header";

export default function Landing() {
  return (
    <div className="page">
      <Header />
      <main className="hero">
        <h1>
          Every business has a story.
          <br />
          <span className="accent">Narada</span> makes the three worlds hear it.
        </h1>
        <p className="pitch">
          Narada is your AI marketing agency: a manager agent and its ganas —
          researcher, copywriter, publisher, analyst — that study your
          business, write your brand brief, and run real campaigns on
          LinkedIn, email, and Telegram while you watch every task, trace, and
          dollar in one dashboard. You approve; the three worlds hear.
        </p>
        <a href="#/start" className="btn-primary big">
          Get started
        </a>

        <section className="pricing">
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
        </section>
      </main>
      <footer className="footer">
        Built on Hermes for the GrowthX Buildathon.
      </footer>
    </div>
  );
}
