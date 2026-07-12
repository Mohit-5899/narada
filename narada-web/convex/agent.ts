// Internal mutations invoked by the Hermes backend through POST /api/agent
// (see http.ts). All writes are keyed by the business link_token — the same
// token minted at onboarding and embedded in the Telegram deep link.
import { internalMutation, type MutationCtx } from "./_generated/server";
import { v } from "convex/values";
import { briefStatus } from "./schema";

async function businessByToken(ctx: MutationCtx, link_token: string) {
  const business = await ctx.db
    .query("businesses")
    .withIndex("by_link_token", (q) => q.eq("link_token", link_token))
    .first();
  if (!business) throw new Error("Unknown link_token");
  return business;
}

export const writeBrief = internalMutation({
  args: {
    link_token: v.string(),
    status: v.optional(briefStatus),
    offering: v.optional(v.string()),
    audience: v.optional(v.string()),
    tone: v.optional(v.array(v.string())),
    competitors: v.optional(v.array(v.string())),
    colors: v.optional(v.array(v.string())),
    campaign_ideas: v.optional(v.array(v.string())),
  },
  handler: async (ctx, { link_token, ...fields }) => {
    const business = await businessByToken(ctx, link_token);
    const brief = await ctx.db
      .query("brand_briefs")
      .withIndex("by_business", (q) => q.eq("business_id", business._id))
      .first();
    if (!brief) throw new Error("No brief for business");
    await ctx.db.patch(brief._id, fields);
    return brief._id;
  },
});

export const linkTelegram = internalMutation({
  args: { link_token: v.string(), telegram_user_id: v.string() },
  handler: async (ctx, { link_token, telegram_user_id }) => {
    const business = await businessByToken(ctx, link_token);
    await ctx.db.patch(business._id, { telegram_user_id });
    return business._id;
  },
});

export const upsertCampaign = internalMutation({
  args: {
    link_token: v.string(),
    campaign_id: v.optional(v.id("campaigns")),
    title: v.optional(v.string()),
    status: v.optional(v.string()),
  },
  handler: async (ctx, { link_token, campaign_id, title, status }) => {
    const business = await businessByToken(ctx, link_token);
    if (campaign_id) {
      const existing = await ctx.db.get(campaign_id);
      if (!existing || existing.business_id !== business._id) {
        throw new Error("Campaign does not belong to this business");
      }
      await ctx.db.patch(campaign_id, {
        ...(title !== undefined ? { title } : {}),
        ...(status !== undefined ? { status } : {}),
      });
      return campaign_id;
    }
    if (!title) throw new Error("title required to create a campaign");
    return await ctx.db.insert("campaigns", {
      business_id: business._id,
      title,
      status: status ?? "planning",
      created_at: Date.now(),
    });
  },
});

export const upsertTask = internalMutation({
  args: {
    campaign_id: v.id("campaigns"),
    task_id: v.optional(v.id("tasks")),
    agent_role: v.optional(v.string()),
    description: v.optional(v.string()),
    status: v.optional(v.string()),
    cost_usd: v.optional(v.number()),
    trace_url: v.optional(v.string()),
    completed_at: v.optional(v.number()),
  },
  handler: async (ctx, { campaign_id, task_id, ...fields }) => {
    const campaign = await ctx.db.get(campaign_id);
    if (!campaign) throw new Error("Unknown campaign");
    if (task_id) {
      const existing = await ctx.db.get(task_id);
      if (!existing || existing.campaign_id !== campaign_id) {
        throw new Error("Task does not belong to this campaign");
      }
      await ctx.db.patch(task_id, fields);
      return task_id;
    }
    if (!fields.agent_role || !fields.description) {
      throw new Error("agent_role and description required to create a task");
    }
    return await ctx.db.insert("tasks", {
      campaign_id,
      agent_role: fields.agent_role,
      description: fields.description,
      status: fields.status ?? "queued",
      cost_usd: fields.cost_usd,
      trace_url: fields.trace_url,
      created_at: Date.now(),
      completed_at: fields.completed_at,
    });
  },
});
