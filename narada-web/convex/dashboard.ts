import { query } from "./_generated/server";
import { getAuthUserId } from "@convex-dev/auth/server";

// Everything the read-only dashboard needs, in one reactive query.
export const overview = query({
  args: {},
  handler: async (ctx) => {
    const userId = await getAuthUserId(ctx);
    if (!userId) return null;
    const business = await ctx.db
      .query("businesses")
      .withIndex("by_owner", (q) => q.eq("owner", userId))
      .first();
    if (!business) return null;

    const campaigns = await ctx.db
      .query("campaigns")
      .withIndex("by_business", (q) => q.eq("business_id", business._id))
      .order("desc")
      .collect();

    const withTasks = await Promise.all(
      campaigns.map(async (campaign) => ({
        campaign,
        tasks: await ctx.db
          .query("tasks")
          .withIndex("by_campaign", (q) => q.eq("campaign_id", campaign._id))
          .collect(),
      })),
    );

    return { business, campaigns: withTasks };
  },
});
