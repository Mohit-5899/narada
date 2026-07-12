import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";
import { authTables } from "@convex-dev/auth/server";

export const briefStatus = v.union(
  v.literal("analyzing"),
  v.literal("ready"),
  v.literal("approved"),
);

export default defineSchema({
  ...authTables,

  businesses: defineTable({
    name: v.string(),
    website: v.string(),
    logo_url: v.optional(v.string()),
    images: v.array(v.string()),
    one_liner: v.optional(v.string()),
    owner: v.id("users"),
    link_token: v.string(),
    telegram_user_id: v.optional(v.string()),
    created_at: v.number(),
  })
    .index("by_owner", ["owner"])
    .index("by_link_token", ["link_token"]),

  brand_briefs: defineTable({
    business_id: v.id("businesses"),
    status: briefStatus,
    offering: v.optional(v.string()),
    audience: v.optional(v.string()),
    tone: v.optional(v.array(v.string())),
    competitors: v.optional(v.array(v.string())),
    colors: v.optional(v.array(v.string())),
    campaign_ideas: v.optional(v.array(v.string())),
    approved_at: v.optional(v.number()),
  }).index("by_business", ["business_id"]),

  campaigns: defineTable({
    business_id: v.id("businesses"),
    title: v.string(),
    status: v.string(),
    created_at: v.number(),
  }).index("by_business", ["business_id"]),

  tasks: defineTable({
    campaign_id: v.id("campaigns"),
    agent_role: v.string(),
    description: v.string(),
    status: v.string(),
    cost_usd: v.optional(v.number()),
    trace_url: v.optional(v.string()),
    created_at: v.number(),
    completed_at: v.optional(v.number()),
  }).index("by_campaign", ["campaign_id"]),

  // Failure/escalation cases appended by the manager agent (closed-loop evals).
  eval_cases: defineTable({
    business_id: v.id("businesses"),
    brief: v.string(),
    failure: v.string(),
    expected: v.string(),
    created_at: v.number(),
  }).index("by_business", ["business_id"]),
});
