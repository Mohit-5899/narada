// Internal functions invoked by the Hermes backend through POST /api/agent
// (see http.ts). Writes are keyed by the business link_token — the same
// token minted at onboarding and embedded in the Telegram deep link — or by
// business_id once the agent has resolved it via get_business.
import {
  internalMutation,
  internalQuery,
  type MutationCtx,
} from "./_generated/server";
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

async function businessByIdOrToken(
  ctx: MutationCtx,
  business_id?: string,
  link_token?: string,
) {
  if (business_id) {
    const business = await ctx.db.get(business_id as never);
    if (!business) throw new Error("Unknown business_id");
    return business as unknown as { _id: string } & Record<string, unknown>;
  }
  if (link_token) return businessByToken(ctx, link_token);
  throw new Error("business_id or link_token required");
}

export const writeBrief = internalMutation({
  args: {
    link_token: v.optional(v.string()),
    business_id: v.optional(v.id("businesses")),
    status: v.optional(briefStatus),
    offering: v.optional(v.string()),
    audience: v.optional(v.string()),
    tone: v.optional(v.array(v.string())),
    competitors: v.optional(v.array(v.string())),
    colors: v.optional(v.array(v.string())),
    campaign_ideas: v.optional(v.array(v.string())),
  },
  handler: async (ctx, { link_token, business_id, ...fields }) => {
    const business = await businessByIdOrToken(ctx, business_id, link_token);
    const brief = await ctx.db
      .query("brand_briefs")
      .withIndex("by_business", (q) => q.eq("business_id", business._id as never))
      .first();
    if (!brief) throw new Error("No brief for business");
    await ctx.db.patch(brief._id, fields);
    return brief._id;
  },
});

// telegram_user_id -> business + its brand brief. THE identity-resolution
// call the manager skill makes on every inbound Telegram message (D10).
export const getBusinessByTelegram = internalQuery({
  args: { telegram_user_id: v.string() },
  handler: async (ctx, { telegram_user_id }) => {
    const business = await ctx.db
      .query("businesses")
      .filter((q) => q.eq(q.field("telegram_user_id"), telegram_user_id))
      .first();
    if (!business) return null;
    const brief = await ctx.db
      .query("brand_briefs")
      .withIndex("by_business", (q) => q.eq("business_id", business._id))
      .first();
    return { business, brief };
  },
});

export const getTasks = internalQuery({
  args: { business_id: v.id("businesses"), limit: v.optional(v.number()) },
  handler: async (ctx, { business_id, limit }) => {
    const campaigns = await ctx.db
      .query("campaigns")
      .withIndex("by_business", (q) => q.eq("business_id", business_id))
      .collect();
    const nested = await Promise.all(
      campaigns.map((c) =>
        ctx.db
          .query("tasks")
          .withIndex("by_campaign", (q) => q.eq("campaign_id", c._id))
          .collect(),
      ),
    );
    return nested
      .flat()
      .sort((a, b) => b.created_at - a.created_at)
      .slice(0, limit ?? 50);
  },
});

// Business-keyed task logging (D9: general chat, campaigns optional).
// Finds-or-creates a "General" campaign so the dashboard needs no changes.
export const logTask = internalMutation({
  args: {
    business_id: v.id("businesses"),
    agent_role: v.string(),
    description: v.string(),
    status: v.string(),
    cost_usd: v.optional(v.number()),
    trace_url: v.optional(v.string()),
  },
  handler: async (ctx, { business_id, ...fields }) => {
    const business = await ctx.db.get(business_id);
    if (!business) throw new Error("Unknown business_id");
    let general = await ctx.db
      .query("campaigns")
      .withIndex("by_business", (q) => q.eq("business_id", business_id))
      .filter((q) => q.eq(q.field("title"), "General"))
      .first();
    if (!general) {
      const id = await ctx.db.insert("campaigns", {
        business_id,
        title: "General",
        status: "active",
        created_at: Date.now(),
      });
      general = await ctx.db.get(id);
    }
    const done = fields.status === "done" || fields.status === "failed";
    return await ctx.db.insert("tasks", {
      campaign_id: general!._id,
      ...fields,
      created_at: Date.now(),
      completed_at: done ? Date.now() : undefined,
    });
  },
});

export const appendEvalCase = internalMutation({
  args: {
    business_id: v.id("businesses"),
    brief: v.string(),
    failure: v.string(),
    expected: v.string(),
  },
  handler: async (ctx, args) => {
    const business = await ctx.db.get(args.business_id);
    if (!business) throw new Error("Unknown business_id");
    return await ctx.db.insert("eval_cases", { ...args, created_at: Date.now() });
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
