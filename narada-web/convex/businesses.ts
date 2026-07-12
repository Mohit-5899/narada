import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { getAuthUserId } from "@convex-dev/auth/server";

function randomToken(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export const getMine = query({
  args: {},
  handler: async (ctx) => {
    const userId = await getAuthUserId(ctx);
    if (!userId) return null;
    return await ctx.db
      .query("businesses")
      .withIndex("by_owner", (q) => q.eq("owner", userId))
      .first();
  },
});

export const generateUploadUrl = mutation({
  args: {},
  handler: async (ctx) => {
    const userId = await getAuthUserId(ctx);
    if (!userId) throw new Error("Not signed in");
    return await ctx.storage.generateUploadUrl();
  },
});

export const create = mutation({
  args: {
    name: v.string(),
    website: v.string(),
    one_liner: v.optional(v.string()),
    logo_id: v.optional(v.id("_storage")),
    image_ids: v.array(v.id("_storage")),
    pdf_ids: v.optional(v.array(v.id("_storage"))),
  },
  handler: async (ctx, args) => {
    const userId = await getAuthUserId(ctx);
    if (!userId) throw new Error("Not signed in");
    const name = args.name.trim();
    const website = args.website.trim();
    if (!name) throw new Error("Business name is required");
    if (!website) throw new Error("Website URL is required");
    if (args.image_ids.length > 5) throw new Error("Max 5 images");
    if ((args.pdf_ids?.length ?? 0) > 3) throw new Error("Max 3 PDFs");

    const logo_url = args.logo_id
      ? ((await ctx.storage.getUrl(args.logo_id)) ?? undefined)
      : undefined;
    const imageUrls = await Promise.all(
      args.image_ids.map((id) => ctx.storage.getUrl(id)),
    );
    const images = imageUrls.filter((u): u is string => u !== null);
    const pdfUrls = await Promise.all(
      (args.pdf_ids ?? []).map((id) => ctx.storage.getUrl(id)),
    );
    const pdfs = pdfUrls.filter((u): u is string => u !== null);

    const link_token = randomToken();
    const businessId = await ctx.db.insert("businesses", {
      name,
      website,
      logo_url,
      images,
      pdfs: pdfs.length ? pdfs : undefined,
      one_liner: args.one_liner?.trim() || undefined,
      owner: userId,
      link_token,
      created_at: Date.now(),
    });
    // Brief starts in "analyzing"; the Hermes crew flips it to "ready"
    // via POST /api/agent.
    await ctx.db.insert("brand_briefs", {
      business_id: businessId,
      status: "analyzing",
    });
    return { businessId, link_token };
  },
});
