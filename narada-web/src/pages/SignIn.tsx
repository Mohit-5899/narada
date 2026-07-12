import { useState, type FormEvent } from "react";
import { useAuthActions } from "@convex-dev/auth/react";
import Header from "../components/Header";

type Flow = "signUp" | "signIn";

export default function SignIn() {
  const { signIn } = useAuthActions();
  const [flow, setFlow] = useState<Flow>("signUp");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmedEmail = email.trim();
    if (!/^\S+@\S+\.\S+$/.test(trimmedEmail)) {
      setError("Enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn("password", {
        email: trimmedEmail,
        password,
        flow,
        ...(flow === "signUp" && name.trim() ? { name: name.trim() } : {}),
      });
      // Authenticated wrapper in App.tsx takes over from here.
    } catch {
      setError(
        flow === "signUp"
          ? "Could not create the account. If you already have one, switch to Sign in."
          : "Wrong email or password. New here? Switch to Create account.",
      );
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

  const switchFlow = (next: Flow) => {
    setFlow(next);
    setError(null);
  };

  return (
    <div className="page">
      <Header />
      <div className="card auth-card">
        <p className="eyebrow">Narada</p>
        <h2>{flow === "signUp" ? "Create your Narada account" : "Welcome back"}</h2>
        <p className="muted">
          {flow === "signUp"
            ? "Sign up once — your marketing team remembers you."
            : "Sign in with your email and password."}
        </p>
        <form onSubmit={submit}>
          {flow === "signUp" && (
            <input
              type="text"
              placeholder="Your name"
              aria-label="Your name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoComplete="name"
            />
          )}
          <input
            type="email"
            placeholder="you@business.com"
            aria-label="Email address"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
          <input
            type="password"
            placeholder="Password (8+ characters)"
            aria-label="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={flow === "signUp" ? "new-password" : "current-password"}
            required
          />
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? "Working…" : flow === "signUp" ? "Create account" : "Sign in"}
          </button>
        </form>
        {flow === "signUp" ? (
          <button className="btn-ghost" onClick={() => switchFlow("signIn")} disabled={busy}>
            Already have an account? Sign in
          </button>
        ) : (
          <button className="btn-ghost" onClick={() => switchFlow("signUp")} disabled={busy}>
            New to Narada? Create account
          </button>
        )}
        <button className="btn-ghost" onClick={() => void guest()} disabled={busy}>
          Continue as guest (demo)
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
