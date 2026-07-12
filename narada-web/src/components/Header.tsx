import { Authenticated } from "convex/react";
import { useAuthActions } from "@convex-dev/auth/react";
import { convexConfigured } from "../config";

// ponytail: read hash directly — Header re-renders with every route change
// because App re-renders the whole page tree on hashchange.
const isActive = (route: string): boolean =>
  window.location.hash.replace(/^#/, "") === route;

export default function Header() {
  return (
    <header className="header">
      <a href="#/" className="wordmark">
        <span className="accent">✦</span> Narada
      </a>
      <nav aria-label="Main">
        <a href="#/guide" className={isActive("/guide") ? "active" : undefined}>
          Guide
        </a>
        <a href="#/telegram" className={isActive("/telegram") ? "active" : undefined}>
          Telegram
        </a>
        <a href="#/dashboard" className={isActive("/dashboard") ? "active" : undefined}>
          Dashboard
        </a>
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
