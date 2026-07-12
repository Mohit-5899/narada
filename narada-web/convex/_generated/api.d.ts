/* eslint-disable */
/**
 * Generated `api` utility types.
 *
 * Committed so typechecking works before `npx convex dev` runs;
 * codegen will overwrite this file.
 */
import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";
import type * as agent from "../agent.js";
import type * as auth from "../auth.js";
import type * as briefs from "../briefs.js";
import type * as businesses from "../businesses.js";
import type * as dashboard from "../dashboard.js";
import type * as http from "../http.js";

declare const fullApi: ApiFromModules<{
  agent: typeof agent;
  auth: typeof auth;
  briefs: typeof briefs;
  businesses: typeof businesses;
  dashboard: typeof dashboard;
  http: typeof http;
}>;

export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;
