import { Authenticated } from "convex/react";
import { useAuthActions } from "@convex-dev/auth/react";
import { convexConfigured } from "../config";

export default function Header() {
  return (
    <header className="header">
      <a href="#/" className="wordmark">
        <span className="accent">✦</span> Narada
      </a>
      <nav>
        <a href="#/dashboard">Dashboard</a>
        {convexConfigured && (
          <Authenticated>
            <SignOutButton />
          </Authenticated>
        )}
      </nav>
    </header>
  );
}

function SignOutButton() {
  const { signOut } = useAuthActions();
  return (
    <button className="btn-ghost" onClick={() => void signOut()}>
      Sign out
    </button>
  );
}
