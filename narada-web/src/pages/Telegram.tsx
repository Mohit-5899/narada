import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import Header from "../components/Header";
import { TELEGRAM_BOT } from "../config";

export default function Telegram() {
  const business = useQuery(api.businesses.getMine);

  if (business === undefined) {
    return (
      <div className="page center">
        <div className="spinner" />
      </div>
    );
  }
  if (business === null) {
    return (
      <div className="page">
        <Header />
        <div className="card notice">
          <h2>No business yet</h2>
          <p>
            <a href="#/start">Start onboarding</a> first.
          </p>
        </div>
      </div>
    );
  }

  const deepLink = `https://t.me/${TELEGRAM_BOT}?start=${business.link_token}`;

  return (
    <div className="page">
      <Header />
      <div className="card notice handoff">
        <p className="eyebrow">Handoff</p>
        <h2>Your marketing team is ready</h2>
        <p>
          Narada and his ganas now know <strong>{business.name}</strong>. Your
          command center is Telegram — say{" "}
          <em>"launch a campaign"</em> and watch the crew go to work.
        </p>
        <a className="btn-primary big" href={deepLink} target="_blank" rel="noreferrer">
          Open Telegram
        </a>
        {business.telegram_user_id ? (
          <p className="muted">Telegram connected ✓</p>
        ) : (
          <p className="muted">
            The button links your Telegram account to this business — one tap.
          </p>
        )}
        <div className="card" style={{ marginTop: "1rem", textAlign: "left" }}>
          <p className="muted" style={{ marginBottom: "0.4rem" }}>
            Button not working, or connecting from another device? Send this
            command to <strong>@{TELEGRAM_BOT}</strong> yourself (click to
            copy):
          </p>
          <code
            style={{ cursor: "copy", userSelect: "all", display: "block" }}
            title="Click to copy"
            onClick={() =>
              void navigator.clipboard.writeText(`/start ${business.link_token}`)
            }
          >
            /start {business.link_token}
          </code>
        </div>
        <p>
          <a href="#/dashboard">Or watch the live dashboard →</a>
        </p>
      </div>
    </div>
  );
}
