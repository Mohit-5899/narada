import { useState, type FormEvent } from "react";
import { useAuthActions } from "@convex-dev/auth/react";
import Header from "../components/Header";

export default function SignIn() {
  const { signIn } = useAuthActions();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const sendLink = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = email.trim();
    if (!/^\S+@\S+\.\S+$/.test(trimmed)) {
      setError("Enter a valid email address.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn("resend", { email: trimmed });
      setSent(true);
    } catch {
      setError(
        "Could not send the magic link. Is AUTH_RESEND_KEY set on the deployment? You can continue as guest below.",
      );
    } finally {
      setBusy(false);
    }
  };

  const guest = async () => {
    setBusy(true);
    setError(null);
    try {
      await signIn("anonymous");
    } catch {
      setError("Guest sign-in failed. Check that `npx convex dev` is running.");
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <Header />
      <div className="card auth-card">
        {sent ? (
          <>
            <h2>Check your email</h2>
            <p>
              We sent a magic link to <strong>{email}</strong>. Click it and
              you'll land right back here, signed in.
            </p>
          </>
        ) : (
          <>
            <h2>Sign in to Narada</h2>
            <p className="muted">Magic link — no password, ever.</p>
            <form onSubmit={sendLink}>
              <input
                type="email"
                placeholder="you@business.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
              <button className="btn-primary" type="submit" disabled={busy}>
                {busy ? "Sending…" : "Send magic link"}
              </button>
            </form>
            <button className="btn-ghost" onClick={() => void guest()} disabled={busy}>
              Continue as guest (demo)
            </button>
            {error && <p className="error">{error}</p>}
          </>
        )}
      </div>
    </div>
  );
}
