import { convexAuth } from "@convex-dev/auth/server";
import { Password } from "@convex-dev/auth/providers/Password";
import { Anonymous } from "@convex-dev/auth/providers/Anonymous";

// Classic email + password auth (supersedes D8 magic link — decision log
// 2026-07-12): sign up once with name/email/password, sign in with the same
// credentials forever after. Anonymous stays as the judge-friendly demo path.
export const { auth, signIn, signOut, store, isAuthenticated } = convexAuth({
  providers: [
    Password({
      profile(params) {
        const name = typeof params.name === "string" && params.name ? params.name : null;
        return {
          email: params.email as string,
          ...(name ? { name } : {}),
        };
      },
    }),
    Anonymous,
  ],
});
