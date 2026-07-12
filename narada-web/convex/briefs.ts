import { mutation, query, type MutationCtx } from "./_generated/server";
import type { Id } from "./_generated/dataModel";
import { v } from "convex/values";
import { getAuthUserId } from "@convex-dev/auth/server";

async function myBrief(ctx: MutationCtx, briefId: Id<"brand_briefs">) {
  const userId = await getAuthUserId(ctx);
  if (!userId) throw new Error("Not signed in");
  const brief = await ctx.db.get(briefId);
  if (!brief) throw new Error("Brief not found");
  const business = await ctx.db.get(brief.business_id);
  if (!business || business.owner !== userId) throw new Error("Not your brief");
  return brief;
}

export const getMine = query({
  args: {},
  handler: async (ctx) => {
    const userId = await getAuthUserId(ctx);
    if (!userId) return null;
    const business = await ctx.db
      .query("businesses")
      .withIndex("by_owner", (q) => q.eq("owner", userId))
      .first();
    if (!business) return null;
    const brief = await ctx.db
      .query("brand_briefs")
      .withIndex("by_business", (q) => q.eq("business_id", business._id))
      .first();
    return brief ? { brief, business } : null;
  },
});

export const update = mutation({
  args: {
    brief_id: v.id("brand_briefs"),
    offering: v.optional(v.string()),
    audience: v.optional(v.string()),
    tone: v.optional(v.array(v.string())),
    competitors: v.optional(v.array(v.string())),
    colors: v.optional(v.array(v.string())),
    campaign_ideas: v.optional(v.array(v.string())),
    context_md: v.optional(v.string()),
  },
  handler: async (ctx, { brief_id, ...fields }) => {
    await myBrief(ctx, brief_id);
    await ctx.db.patch(brief_id, fields);
  },
});

export const approve = mutation({
  args: { brief_id: v.id("brand_briefs") },
  handler: async (ctx, { brief_id }) => {
    await myBrief(ctx, brief_id);
    await ctx.db.patch(brief_id, {
      status: "approved",
      approved_at: Date.now(),
    });
  },
});

// ponytail: demo fallback so the flow is walkable before the Hermes crew is
// wired up. Owner-gated; remove once /api/agent is live end-to-end.
export const devSeed = mutation({
  args: { brief_id: v.id("brand_briefs") },
  handler: async (ctx, { brief_id }) => {
    const brief = await myBrief(ctx, brief_id);
    if (brief.status !== "analyzing") return;
    await ctx.db.patch(brief_id, {
      status: "ready",
      offering: "Premium Bengali OTT streaming for global audiences",
      audience: "Bengali diaspora, 25-45, mobile-first entertainment lovers",
      tone: ["warm", "cultural", "bold"],
      competitors: ["Netflix", "ZEE5", "SonyLIV"],
      colors: ["#FF9933", "#0d0d10", "#f5efe6"],
      campaign_ideas: [
        "Diaspora Diwali watch-party campaign on Instagram",
        "LinkedIn thought-leadership: the rise of regional OTT",
        "Email win-back series for lapsed subscribers",
        "Telegram channel: daily 60-second show trailers",
        "Landing page A/B test: family plan vs. solo plan",
      ],
    });
  },
});
