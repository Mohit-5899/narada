import Header from "../components/Header";

// ponytail: Dodo Payments checkout lands here later; today it's an honest stub.
export default function Checkout() {
  return (
    <div className="page">
      <Header />
      <div className="card notice">
        <h2>Checkout coming right up</h2>
        <p>
          Dodo Payments integration is on the way. Meanwhile, onboarding is
          free — <a href="#/start">get your brand brief</a>.
        </p>
      </div>
    </div>
  );
}
