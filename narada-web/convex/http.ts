import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { internal } from "./_generated/api";
import { auth } from "./auth";

const http = httpRouter();

// Convex Auth routes (magic-link callback etc.)
auth.addHttpRoutes(http);

// Single agent-facing endpoint. The Hermes backend authenticates with the
// AGENT_SHARED_SECRET deployment env var:
//   curl -X POST $CONVEX_SITE_URL/api/agent \
//     -H "x-agent-secret: $AGENT_SHARED_SECRET" -H "content-type: application/json" \
//     -d '{"type":"brief","link_token":"...","status":"ready","offering":"..."}'
//
// Payload types:
//   brief          — patch brand brief fields / status (keyed by link_token)
//   telegram_link  — bind telegram_user_id to a business (keyed by link_token)
//   campaign       — create or update a campaign; response carries its id
//   task           — create or update a task under a campaign
http.route({
  path: "/api/agent",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const secret = process.env.AGENT_SHARED_SECRET;
    if (!secret || request.headers.get("x-agent-secret") !== secret) {
      return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), {
        status: 401,
        headers: { "content-type": "application/json" },
      });
    }

    let body: Record<string, unknown>;
    try {
      body = await request.json();
    } catch {
      return badRequest("invalid JSON body");
    }
    if (typeof body !== "object" || body === null) {
      return badRequest("body must be a JSON object");
    }

    try {
      switch (body.type) {
        case "get_business": {
          const result = await ctx.runQuery(internal.agent.getBusinessByTelegram, {
            telegram_user_id: str(body, "telegram_user_id"),
          });
          return ok({ result });
        }
        case "get_tasks": {
          const result = await ctx.runQuery(internal.agent.getTasks, {
            business_id: str(body, "business_id") as never,
            limit: typeof body.limit === "number" ? body.limit : undefined,
          });
          return ok({ result });
        }
        case "log_task": {
          const id = await ctx.runMutation(internal.agent.logTask, {
            business_id: str(body, "business_id") as never,
            agent_role: str(body, "agent_role"),
            description: str(body, "description"),
            status: str(body, "status"),
            cost_usd: typeof body.cost_usd === "number" ? body.cost_usd : undefined,
            trace_url: optStr(body, "trace_url"),
          });
          return ok({ task_id: id });
        }
        case "eval_case": {
          const id = await ctx.runMutation(internal.agent.appendEvalCase, {
            business_id: str(body, "business_id") as never,
            brief: str(body, "brief"),
            failure: str(body, "failure"),
            expected: str(body, "expected"),
          });
          return ok({ eval_case_id: id });
        }
        case "brief": {
          const id = await ctx.runMutation(internal.agent.writeBrief, {
            link_token: optStr(body, "link_token"),
            business_id: optStr(body, "business_id") as never,
            status: body.status as never,
            offering: optStr(body, "offering"),
            audience: optStr(body, "audience"),
            tone: optStrArr(body, "tone"),
            competitors: optStrArr(body, "competitors"),
            colors: optStrArr(body, "colors"),
            campaign_ideas: optStrArr(body, "campaign_ideas"),
          });
          return ok({ brief_id: id });
        }
        case "telegram_link": {
          const id = await ctx.runMutation(internal.agent.linkTelegram, {
            link_token: str(body, "link_token"),
            telegram_user_id: str(body, "telegram_user_id"),
          });
          return ok({ business_id: id });
        }
        case "campaign": {
          const id = await ctx.runMutation(internal.agent.upsertCampaign, {
            link_token: str(body, "link_token"),
            campaign_id: body.campaign_id as never,
            title: optStr(body, "title"),
            status: optStr(body, "status"),
          });
          return ok({ campaign_id: id });
        }
        case "task": {
          const id = await ctx.runMutation(internal.agent.upsertTask, {
            campaign_id: str(body, "campaign_id") as never,
            task_id: body.task_id as never,
            agent_role: optStr(body, "agent_role"),
            description: optStr(body, "description"),
            status: optStr(body, "status"),
            cost_usd: typeof body.cost_usd === "number" ? body.cost_usd : undefined,
            trace_url: optStr(body, "trace_url"),
            completed_at:
              typeof body.completed_at === "number" ? body.completed_at : undefined,
          });
          return ok({ task_id: id });
        }
        default:
          return badRequest(
            "unknown type (brief|telegram_link|campaign|task|get_business|get_tasks|log_task|eval_case)",
          );
      }
    } catch (error) {
      // Convex validators + mutations enforce the real invariants; surface
      // their message so the agent can self-correct.
      return badRequest(error instanceof Error ? error.message : "write failed");
    }
  }),
});

function ok(data: Record<string, unknown>): Response {
  return new Response(JSON.stringify({ ok: true, ...data }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function badRequest(error: string): Response {
  return new Response(JSON.stringify({ ok: false, error }), {
    status: 400,
    headers: { "content-type": "application/json" },
  });
}

function str(body: Record<string, unknown>, key: string): string {
  const value = body[key];
  if (typeof value !== "string" || !value) throw new Error(`${key} required`);
  return value;
}

function optStr(body: Record<string, unknown>, key: string): string | undefined {
  const value = body[key];
  return typeof value === "string" ? value : undefined;
}

function optStrArr(body: Record<string, unknown>, key: string): string[] | undefined {
  const value = body[key];
  if (!Array.isArray(value)) return undefined;
  return value.filter((item): item is string => typeof item === "string");
}

export default http;
