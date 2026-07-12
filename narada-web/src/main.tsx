import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ConvexReactClient } from "convex/react";
import { ConvexAuthProvider } from "@convex-dev/auth/react";
import App from "./App";
import { CONVEX_URL } from "./config";
import "./index.css";

const root = createRoot(document.getElementById("root")!);

// Without VITE_CONVEX_URL the app still renders (landing + setup notice);
// with it, the full authed flow lights up.
if (CONVEX_URL) {
  const convex = new ConvexReactClient(CONVEX_URL);
  root.render(
    <StrictMode>
      <ConvexAuthProvider client={convex}>
        <App />
      </ConvexAuthProvider>
    </StrictMode>,
  );
} else {
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
