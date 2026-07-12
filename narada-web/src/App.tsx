import { useEffect, useState, type ReactElement } from "react";
import { Authenticated, AuthLoading, Unauthenticated } from "convex/react";
import { convexConfigured } from "./config";
import Landing from "./pages/Landing";
import SignIn from "./pages/SignIn";
import Start from "./pages/Start";
import Brief from "./pages/Brief";
import Telegram from "./pages/Telegram";
import Dashboard from "./pages/Dashboard";
import Checkout from "./pages/Checkout";
import Guide from "./pages/Guide";
import Header from "./components/Header";

// ponytail: 20-line hash router instead of react-router — five static routes,
// works on any static host. Swap for react-router if nesting ever appears.
function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash.replace(/^#/, "") || "/";
}

const AUTHED_ROUTES: Record<string, () => ReactElement> = {
  "/start": () => <Start />,
  "/brief": () => <Brief />,
  "/telegram": () => <Telegram />,
  "/dashboard": () => <Dashboard />,
};

export default function App() {
  const route = useHashRoute();

  if (route === "/") return <Landing />;
  if (route === "/checkout") return <Checkout />;
  if (route === "/guide") return <Guide />;

  const render = AUTHED_ROUTES[route];
  if (!render) return <Landing />;

  if (!convexConfigured) {
    return (
      <div className="page">
        <Header />
        <div className="card notice">
          <h2>Backend not connected</h2>
          <p>
            Set <code>VITE_CONVEX_URL</code> in <code>.env.local</code> (run{" "}
            <code>npx convex dev</code> to get one), then reload. See the
            README for the 3-command activation checklist.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <AuthLoading>
        <div className="page center">
          <div className="spinner" />
        </div>
      </AuthLoading>
      <Unauthenticated>
        <SignIn />
      </Unauthenticated>
      <Authenticated>{render()}</Authenticated>
    </>
  );
}
