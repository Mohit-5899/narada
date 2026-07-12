import Header from "../components/Header";

// Dodo Payments live checkout (test mode for the buildathon).
const DODO_CHECKOUT_URL =
  "https://test.checkout.dodopayments.com/buy/pdt_0Nj13OjtcRdHTFRSEX287?quantity=1";

export default function Checkout() {
  return (
    <div className="page">
      <Header />
      <div className="card notice">
        <p className="eyebrow">Narada Hosted · $9/mo</p>
        <h2>Hire your marketing team</h2>
        <p>
          Full agent crew — researcher, copywriter, creative, publisher,
          analyst — managed for you. Real publishing to LinkedIn, Instagram,
          X, and YouTube. Cancel anytime.
        </p>
        <a href={DODO_CHECKOUT_URL} className="btn-primary big">
          Subscribe — $9/month
        </a>
        <p className="muted" style={{ marginTop: "1rem" }}>
          Secure checkout by Dodo Payments. Or start free —{" "}
          <a href="#/start">get your brand brief</a> first.
        </p>
      </div>
    </div>
  );
}
