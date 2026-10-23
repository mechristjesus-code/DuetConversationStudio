import { z } from "zod";
import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import {
  createGeneration,
  createSource,
  listGenerations,
  listSources,
  getOrCreateDefaultProject,
  getProjectManifest,
  setGenerationRenderStatus,
} from "./db";

const sourceInput = z.object({
  originalName: z.string().min(1).max(255),
  originalReference: z.string().max(2048).optional(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/i),
  sizeBytes: z.number().int().nonnegative().optional(),
  durationMs: z.number().int().nonnegative().optional(),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
  hasAudio: z.boolean().default(false),
  videoCodec: z.string().max(64).optional(),
  audioCodec: z.string().max(64).optional(),
});

const recipeInput = z.object({
  sourceId: z.number().int().positive().optional(),
  generationId: z.number().int().positive().optional(),
  trimStartMs: z.number().int().nonnegative().default(0),
  trimEndMs: z.number().int().positive().nullable().optional(),
  syncOffsetMs: z.number().int().default(0),
  gain: z.number().min(0).max(8).default(1),
  muted: z.boolean().default(false),
}).superRefine((value, ctx) => {
  if ((value.sourceId === undefined) === (value.generationId === undefined)) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Provide exactly one of sourceId or generationId" });
  }
});

const portableRecipe = z.object({
  schema_version: z.number().int().positive().default(1),
  layout: z.record(z.string(), z.unknown()).default({ type: "split_screen", direction: "horizontal" }),
  canvas: z.record(z.string(), z.unknown()).optional(),
  audio: z.record(z.string(), z.unknown()).optional(),
});

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return { success: true } as const;
    }),
  }),
  protocol: publicProcedure.query(() => ({
    edition: "online",
    protocolVersion: 1,
    termuxCompatible: true,
    renderCapability: "media_unavailable",
    statusValues: ["draft", "queued", "processing", "completed", "failed", "media_unavailable"],
    distributionProfiles: {
      tiktok: {
        width: 1080,
        height: 1920,
        aspectRatio: "9:16",
        videoCodec: "H.264",
        audioCodec: "AAC",
        postingMode: "manual_review_only",
        directPostingEnabled: false,
        attribution: "caption_credit_plus_tiktok_video_credit_control",
      },
    },
    note: "Online records use the same portable recipe and lineage shape as the Termux edition. A real online MP4 requires a connected durable media runtime.",
  })),
  project: router({
    current: publicProcedure.query(() => getOrCreateDefaultProject()),
  }),
  sync: router({
    manifest: publicProcedure.query(() => getProjectManifest()),
  }),
  sources: router({
    list: publicProcedure.query(() => listSources()),
    register: publicProcedure.input(sourceInput).mutation(async ({ input }) => {
      const project = await getOrCreateDefaultProject();
      return createSource({
        projectId: project.id,
        sourceUuid: `src-${crypto.randomUUID()}`,
        originalName: input.originalName,
        originalReference: input.originalReference,
        managedKey: null,
        sha256: input.sha256,
        sizeBytes: input.sizeBytes,
        durationMs: input.durationMs,
        width: input.width,
        height: input.height,
        hasAudio: input.hasAudio ? 1 : 0,
        videoCodec: input.videoCodec,
        audioCodec: input.audioCodec,
        status: "browser_only",
      });
    }),
  }),
  generations: router({
    list: publicProcedure.query(() => listGenerations()),
    create: publicProcedure.input(z.object({
      recipe: portableRecipe.optional(),
      inputs: z.array(recipeInput).length(2),
    })).mutation(async ({ input }) => {
      const available = await listSources();
      const availableGenerations = await listGenerations();
      const byId = new Map(available.map((source) => [source.id, source]));
      const generationById = new Map(availableGenerations.map((generation) => [generation.id, generation]));
      const refs = input.inputs.map((item, ordinal) => {
        if (item.trimEndMs !== null && item.trimEndMs !== undefined && item.trimEndMs <= item.trimStartMs) {
          throw new Error(`Input ${ordinal + 1} has an invalid trim range`);
        }
        if (item.sourceId !== undefined) {
          const source = byId.get(item.sourceId);
          if (!source) throw new Error(`Source ${item.sourceId} was not found`);
          return {
            ordinal,
            refKind: "source" as const,
            sourceId: item.sourceId,
            parentGenerationId: null,
            trimStartMs: item.trimStartMs,
            trimEndMs: item.trimEndMs ?? null,
            syncOffsetMs: item.syncOffsetMs,
            gain: Math.round(item.gain * 1000),
            muted: item.muted ? 1 : 0,
            sourceSha256: source.sha256,
          };
        }
        const parent = generationById.get(item.generationId!);
        if (!parent) throw new Error(`Generation ${item.generationId} was not found`);
        if (parent.renderStatus !== "completed" || !parent.renderSha256) {
          throw new Error(`Generation ${item.generationId} is not a completed media render`);
        }
        return {
          ordinal,
          refKind: "generation" as const,
          sourceId: null,
          parentGenerationId: item.generationId,
          trimStartMs: item.trimStartMs,
          trimEndMs: item.trimEndMs ?? null,
          syncOffsetMs: item.syncOffsetMs,
          gain: Math.round(item.gain * 1000),
          muted: item.muted ? 1 : 0,
          sourceSha256: parent.renderSha256,
        };
      });
      const recipe = {
        schema_version: input.recipe?.schema_version ?? 1,
        layout: input.recipe?.layout ?? { type: "split_screen", direction: "horizontal" },
        canvas: input.recipe?.canvas ?? { width: 1920, height: 1080, fps: 30 },
        audio: input.recipe?.audio ?? { mix: "amix", duration: "longest" },
        inputs: input.inputs.map((item) => item.sourceId !== undefined ? {
          ...item,
          sourceUuid: byId.get(item.sourceId)!.sourceUuid,
          sourceSha256: byId.get(item.sourceId)!.sha256,
        } : {
          ...item,
          parentGenerationUuid: generationById.get(item.generationId!)!.generationUuid,
          parentRenderSha256: generationById.get(item.generationId!)!.renderSha256,
        }),
      };
      const existing = await listGenerations();
      const generationNumber = existing.reduce((max, generation) => Math.max(max, generation.generationNumber), 0) + 1;
      const project = await getOrCreateDefaultProject();
      return createGeneration({
        projectId: project.id,
        generationUuid: `gen-${crypto.randomUUID()}`,
        generationNumber,
        recipeJson: JSON.stringify(recipe),
        renderStatus: "draft",
      }, refs);
    }),
    requestRender: publicProcedure.input(z.object({ generationId: z.number().int().positive() })).mutation(({ input }) =>
      setGenerationRenderStatus(input.generationId, "media_unavailable", "Online media runtime is not connected yet. Use the Termux edition for an offline FFmpeg render, or connect approved durable media storage and a render worker.")),
  }),
});

export type AppRouter = typeof appRouter;
