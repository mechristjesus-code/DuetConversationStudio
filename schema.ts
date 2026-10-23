import {
  bigint,
  index,
  int,
  mysqlEnum,
  mysqlTable,
  text,
  timestamp,
  varchar,
} from "drizzle-orm/mysql-core";

export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

export const projects = mysqlTable("duet_projects", {
  id: int("id").autoincrement().primaryKey(),
  projectUuid: varchar("projectUuid", { length: 80 }).notNull().unique(),
  name: varchar("name", { length: 160 }).notNull(),
  revision: int("revision").notNull().default(1),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Project = typeof projects.$inferSelect;
export type InsertProject = typeof projects.$inferInsert;

export const sources = mysqlTable("duet_sources", {
  id: int("id").autoincrement().primaryKey(),
  projectId: int("projectId").references(() => projects.id, { onDelete: "cascade" }),
  sourceUuid: varchar("sourceUuid", { length: 80 }).notNull().unique(),
  originalName: varchar("originalName", { length: 255 }).notNull(),
  originalReference: text("originalReference"),
  managedKey: text("managedKey"),
  sha256: varchar("sha256", { length: 64 }).notNull(),
  sizeBytes: bigint("sizeBytes", { mode: "number" }),
  durationMs: int("durationMs"),
  width: int("width"),
  height: int("height"),
  hasAudio: int("hasAudio").notNull().default(0),
  videoCodec: varchar("videoCodec", { length: 64 }),
  audioCodec: varchar("audioCodec", { length: 64 }),
  status: mysqlEnum("status", ["ok", "browser_only", "missing", "changed", "media_unavailable"]).notNull().default("browser_only"),
  importedAt: timestamp("importedAt").defaultNow().notNull(),
  lastVerifiedAt: timestamp("lastVerifiedAt"),
  lastError: text("lastError"),
}, (table) => ({
  sourceHashIdx: index("duet_sources_sha256_idx").on(table.sha256),
  projectIdx: index("duet_sources_project_idx").on(table.projectId),
}));

export type Source = typeof sources.$inferSelect;
export type InsertSource = typeof sources.$inferInsert;

export const generations = mysqlTable("duet_generations", {
  id: int("id").autoincrement().primaryKey(),
  projectId: int("projectId").references(() => projects.id, { onDelete: "cascade" }),
  generationUuid: varchar("generationUuid", { length: 80 }).notNull().unique(),
  generationNumber: int("generationNumber").notNull().unique(),
  recipeJson: text("recipeJson").notNull(),
  renderStatus: mysqlEnum("renderStatus", ["draft", "queued", "processing", "completed", "failed", "media_unavailable"]).notNull().default("draft"),
  renderPath: text("renderPath"),
  renderSha256: varchar("renderSha256", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  renderedAt: timestamp("renderedAt"),
  error: text("error"),
}, (table) => ({
  projectIdx: index("duet_generations_project_idx").on(table.projectId),
}));

export type Generation = typeof generations.$inferSelect;
export type InsertGeneration = typeof generations.$inferInsert;

export const inputRefs = mysqlTable("duet_input_refs", {
  id: int("id").autoincrement().primaryKey(),
  generationId: int("generationId").notNull().references(() => generations.id, { onDelete: "cascade" }),
  ordinal: int("ordinal").notNull(),
  refKind: mysqlEnum("refKind", ["source", "generation"]).notNull().default("source"),
  sourceId: int("sourceId").references(() => sources.id, { onDelete: "restrict" }),
  parentGenerationId: int("parentGenerationId").references(() => generations.id, { onDelete: "restrict" }),
  trimStartMs: int("trimStartMs").notNull().default(0),
  trimEndMs: int("trimEndMs"),
  syncOffsetMs: int("syncOffsetMs").notNull().default(0),
  gain: int("gainMilli").notNull().default(1000),
  muted: int("muted").notNull().default(0),
  sourceSha256: varchar("sourceSha256", { length: 64 }),
}, (table) => ({
  generationOrdinalIdx: index("duet_input_refs_generation_idx").on(table.generationId, table.ordinal),
}));

export type InputRef = typeof inputRefs.$inferSelect;
export type InsertInputRef = typeof inputRefs.$inferInsert;
