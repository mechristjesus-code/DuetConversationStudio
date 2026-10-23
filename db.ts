import { desc, eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import {
  generations,
  inputRefs,
  InsertGeneration,
  InsertInputRef,
  InsertSource,
  InsertUser,
  projects,
  sources,
  users,
} from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    throw new Error("Database is not available");
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function getOrCreateDefaultProject() {
  const db = await getDb();
  if (!db) throw new Error("Database is not available");
  const existing = await db.select().from(projects).limit(1);
  if (existing[0]) return existing[0];
  const result = await db.insert(projects).values({
    projectUuid: `project-${crypto.randomUUID()}`,
    name: "Duet Conversation Studio",
    revision: 1,
  });
  const rows = await db.select().from(projects).where(eq(projects.id, Number(result[0].insertId))).limit(1);
  return rows[0];
}

export async function getProjectManifest() {
  const db = await getDb();
  if (!db) throw new Error("Database is not available");
  const project = await getOrCreateDefaultProject();
  const projectSources = await db.select().from(sources).where(eq(sources.projectId, project.id));
  const projectGenerations = await db.select().from(generations).where(eq(generations.projectId, project.id));
  const refs = await db.select().from(inputRefs);
  return {
    protocolVersion: 1,
    project,
    sources: projectSources,
    generations: projectGenerations.map((generation) => ({
      ...generation,
      recipe: JSON.parse(generation.recipeJson),
      inputRefs: refs.filter((ref) => ref.generationId === generation.id),
    })),
  };
}

export async function listSources() {
  const db = await getDb();
  if (!db) return [];
  const project = await getOrCreateDefaultProject();
  return db.select().from(sources).where(eq(sources.projectId, project.id)).orderBy(desc(sources.importedAt));
}

export async function createSource(source: InsertSource) {
  const db = await getDb();
  if (!db) throw new Error("Database is not available");
  const result = await db.insert(sources).values(source);
  const id = Number(result[0].insertId);
  const rows = await db.select().from(sources).where(eq(sources.id, id)).limit(1);
  return rows[0];
}

export async function listGenerations() {
  const db = await getDb();
  if (!db) return [];
  const project = await getOrCreateDefaultProject();
  const rows = await db.select().from(generations).where(eq(generations.projectId, project.id)).orderBy(desc(generations.generationNumber));
  const refs = await db.select().from(inputRefs);
  return rows.map((generation) => ({
    ...generation,
    recipe: JSON.parse(generation.recipeJson),
    inputRefs: refs.filter((ref) => ref.generationId === generation.id),
  }));
}

export async function createGeneration(
  generation: InsertGeneration,
  refs: Omit<InsertInputRef, "generationId">[],
) {
  const db = await getDb();
  if (!db) throw new Error("Database is not available");
  return db.transaction(async (tx) => {
    const inserted = await tx.insert(generations).values(generation);
    const id = Number(inserted[0].insertId);
    if (refs.length) {
      await tx.insert(inputRefs).values(refs.map((ref) => ({ ...ref, generationId: id })));
    }
    const rows = await tx.select().from(generations).where(eq(generations.id, id)).limit(1);
    return rows[0];
  });
}

export async function setGenerationRenderStatus(
  id: number,
  renderStatus: "draft" | "queued" | "processing" | "completed" | "failed" | "media_unavailable",
  error?: string,
) {
  const db = await getDb();
  if (!db) throw new Error("Database is not available");
  await db.update(generations).set({ renderStatus, error: error ?? null }).where(eq(generations.id, id));
  const rows = await db.select().from(generations).where(eq(generations.id, id)).limit(1);
  return rows[0];
}
