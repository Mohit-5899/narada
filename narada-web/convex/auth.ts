import { convexAuth } from "@convex-dev/auth/server";
import Resend from "@auth/core/providers/resend";
import { Anonymous } from "@convex-dev/auth/providers/Anonymous";

// Magic-link signup via Resend (D8: email magic-link, no password).
// Anonymous is a demo fallback so the flow works before AUTH_RESEND_KEY is set.
export const { auth, signIn, signOut, store, isAuthenticated } = convexAuth({
  providers: [
    Resend({
      from: process.env.AUTH_EMAIL_FROM ?? "Narada <onboarding@resend.dev>",
    }),
    Anonymous,
  ],
});
