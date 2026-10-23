import { useMemo, useRef, useState } from "react";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { ArrowUpRight, Check, FileVideo, HardDrive, Link2, LockKeyhole, RefreshCw, Upload, Wifi, WifiOff, X } from "lucide-react";

const formatDuration = (ms: number | null | undefined) => {
  if (!ms) return "—";
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};

const hashFile = async (file: File) => {
  const bytes = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest)).map(byte => byte.toString(16).padStart(2, "0")).join("");
};

const readVideoMetadata = (file: File) => new Promise<{ durationMs: number; width: number; height: number }>((resolve, reject) => {
  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.preload = "metadata";
  video.onloadedmetadata = () => {
    resolve({ durationMs: Math.round(video.duration * 1000), width: video.videoWidth, height: video.videoHeight });
    URL.revokeObjectURL(url);
  };
  video.onerror = () => { URL.revokeObjectURL(url); reject(new Error("The browser could not inspect this video.")); };
  video.src = url;
});

function StatusDot({ status }: { status: string }) {
  const color = status === "completed" || status === "ok" ? "bg-emerald-400" : status === "media_unavailable" || status === "failed" ? "bg-orange-400" : "bg-cyan-400";
  return <span className={`inline-block size-2 rounded-full ${color} ${status === "processing" ? "animate-pulse" : ""}`} />;
}

export default function Home() {
  const [selectedA, setSelectedA] = useState<number>();
  const [selectedB, setSelectedB] = useState<number>();
  const [gainA, setGainA] = useState(1);
  const [gainB, setGainB] = useState(1);
  const [muteA, setMuteA] = useState(false);
  const [muteB, setMuteB] = useState(false);
  const [importState, setImportState] = useState("idle");
  const [importError, setImportError] = useState<string>();
  const [renderMessage, setRenderMessage] = useState<string>();
  const inputRef = useRef<HTMLInputElement>(null);
  const utils = trpc.useUtils();
  const protocol = trpc.protocol.useQuery();
  const sources = trpc.sources.list.useQuery();
  const generations = trpc.generations.list.useQuery();
  const registerSource = trpc.sources.register.useMutation({
    onSuccess: () => utils.sources.list.invalidate(),
  });
  const createGeneration = trpc.generations.create.useMutation({
    onSuccess: () => utils.generations.list.invalidate(),
  });
  const requestRender = trpc.generations.requestRender.useMutation({
    onSuccess: (generation) => {
      setRenderMessage(generation?.error ?? "Render status updated.");
      utils.generations.list.invalidate();
    },
  });

  const sourceRows = sources.data ?? [];
  const generationRows = generations.data ?? [];
  const selectedSources = useMemo(() => ({
    a: sourceRows.find(source => source.id === selectedA),
    b: sourceRows.find(source => source.id === selectedB),
  }), [selectedA, selectedB, sourceRows]);

  const importFile = async (file?: File) => {
    if (!file) return;
    setImportError(undefined);
    if (!file.type.startsWith("video/")) { setImportError("Choose a video file."); return; }
    if (file.size > 2 * 1024 * 1024 * 1024) { setImportError("The online milestone accepts files up to 2 GB."); return; }
    try {
      setImportState("inspecting");
      const [metadata, sha256] = await Promise.all([readVideoMetadata(file), hashFile(file)]);
      setImportState("saving");
      const registered = await registerSource.mutateAsync({
        originalName: file.name,
        originalReference: `browser://${file.name}`,
        sha256,
        sizeBytes: file.size,
        durationMs: metadata.durationMs,
        width: metadata.width,
        height: metadata.height,
        hasAudio: false,
      });
      setImportState("done");
      toast.success(`${file.name} registered with its content hash.`);
      if (selectedA === undefined) setSelectedA(registered.id);
      else if (selectedB === undefined) setSelectedB(registered.id);
    } catch (error) {
      setImportState("idle");
      setImportError(error instanceof Error ? error.message : "Import failed.");
    }
  };

  const compose = async () => {
    if (!selectedA || !selectedB) { setRenderMessage("Choose two registered sources first."); return; }
    try {
      const generation = await createGeneration.mutateAsync({
        inputs: [
          { sourceId: selectedA, trimStartMs: 0, trimEndMs: null, syncOffsetMs: 0, gain: gainA, muted: muteA },
          { sourceId: selectedB, trimStartMs: 0, trimEndMs: null, syncOffsetMs: 0, gain: gainB, muted: muteB },
        ],
        recipe: { schema_version: 1, layout: { type: "split_screen", direction: "horizontal" }, canvas: { width: 1920, height: 1080, fps: 30 }, audio: { mix: "amix", duration: "longest" } },
      });
      const result = await requestRender.mutateAsync({ generationId: generation.id });
      setRenderMessage(result?.error ?? "Render status updated.");
      toast.message(`Duet ${String(generation.generationNumber).padStart(3, "0")} recorded.`);
    } catch (error) {
      setRenderMessage(error instanceof Error ? error.message : "Could not save the recipe.");
    }
  };

  return (
    <div className="min-h-screen bg-[#111416] text-[#e7eceb]">
      <header className="border-b border-white/10 bg-[#151a1c]/95">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-4 py-4 sm:px-8">
          <div className="flex items-center gap-3"><div className="flex size-9 items-center justify-center rounded-lg bg-[#f18b3b] text-sm font-black text-[#111416]">DS</div><div><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-300">Duet Conversation</p><h1 className="text-lg font-semibold tracking-tight">Studio <span className="text-white/35">/ Online</span></h1></div></div>
          <div className="flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-cyan-200"><Wifi className="size-3" /> Online records</div>
        </div>
      </header>
      <div className="mx-auto grid max-w-[1440px] gap-0 lg:grid-cols-[220px_minmax(0,1fr)_300px]">
        <aside className="hidden border-r border-white/10 p-6 lg:block"><p className="mb-5 font-mono text-[10px] uppercase tracking-[0.2em] text-white/35">Workspace</p><nav className="space-y-2 text-sm"><div className="rounded-md bg-white/10 px-3 py-2.5 font-medium text-white">Studio <span className="float-right text-cyan-300">01</span></div><div className="px-3 py-2.5 text-white/45">Conversation hub <span className="float-right font-mono text-[10px]">soon</span></div><div className="px-3 py-2.5 text-white/45">Approvals <span className="float-right font-mono text-[10px]">soon</span></div></nav><div className="mt-12 border-t border-white/10 pt-5"><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/35">Bridge</p><p className="mt-3 text-xs leading-5 text-white/55">Recipes and hashes are portable to the offline Termux renderer.</p><div className="mt-4 flex items-center gap-2 text-xs text-emerald-300"><WifiOff className="size-3" /> Termux compatible</div></div></aside>
        <main className="min-w-0 p-4 sm:p-8">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4"><div><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-orange-300">Project / first release</p><h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Make the next response<br /><span className="text-white/40">without losing the chain.</span></h2></div><div className="text-right"><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/35">Protocol</p><p className="mt-1 font-mono text-sm text-cyan-200">v{protocol.data?.protocolVersion ?? 1} · shared recipe</p></div></div>
          <section className="mb-6 rounded-xl border border-white/10 bg-[#181e20] p-4 sm:p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded-lg bg-white/5"><Upload className="size-4 text-cyan-300" /></div><div><h3 className="font-medium">Register source media</h3><p className="text-xs text-white/45">Validate locally in the browser, then save metadata + SHA-256.</p></div></div><Button variant="secondary" className="bg-white/10 text-white hover:bg-white/15" onClick={() => inputRef.current?.click()} disabled={importState === "inspecting" || importState === "saving"}><FileVideo className="mr-2 size-4" />{importState === "inspecting" ? "Inspecting…" : importState === "saving" ? "Saving…" : "Choose video"}</Button><input ref={inputRef} className="hidden" type="file" accept="video/*" onChange={event => importFile(event.target.files?.[0])} /></div>{importError && <p className="mt-3 flex items-center gap-2 text-xs text-orange-300"><X className="size-3" />{importError}</p>}{importState === "done" && <p className="mt-3 flex items-center gap-2 text-xs text-emerald-300"><Check className="size-3" />Source registered. The browser original was not changed.</p>}</section>
          <section className="rounded-xl border border-white/10 bg-[#181e20] p-4 sm:p-5"><div className="mb-5 flex items-start justify-between gap-4"><div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/35">Compose / 02 inputs</p><h3 className="mt-1 text-lg font-medium">Build a split-screen duet</h3></div><Badge className="border border-orange-300/20 bg-orange-300/10 font-mono text-[10px] uppercase tracking-wider text-orange-200">Recipe first</Badge></div><div className="grid gap-3 md:grid-cols-2"><SourceCard label="A" source={selectedSources.a} sources={sourceRows} selected={selectedA} onSelect={setSelectedA} gain={gainA} onGain={setGainA} muted={muteA} onMuted={setMuteA} accent="cyan" /><SourceCard label="B" source={selectedSources.b} sources={sourceRows} selected={selectedB} onSelect={setSelectedB} gain={gainB} onGain={setGainB} muted={muteB} onMuted={setMuteB} accent="orange" /></div><div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4"><div className="flex items-center gap-2 text-xs text-white/45"><HardDrive className="size-3" /> Online render capability: <span className="text-orange-200">media runtime pending</span></div><Button onClick={compose} disabled={createGeneration.isPending || requestRender.isPending || !selectedA || !selectedB} className="bg-[#f18b3b] text-[#111416] hover:bg-[#ff9e4e]"><ArrowUpRight className="mr-2 size-4" />Save recipe & queue</Button></div>{renderMessage && <p className="mt-3 rounded-md border border-orange-300/15 bg-orange-300/5 px-3 py-2 text-xs leading-5 text-orange-100">{renderMessage}</p>}</section>
          <section className="mt-6"><div className="mb-3 flex items-center justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/35">History</p><h3 className="mt-1 text-lg font-medium">Generations</h3></div><Button variant="ghost" size="icon" onClick={() => { utils.sources.list.invalidate(); utils.generations.list.invalidate(); }} className="text-white/50 hover:bg-white/10 hover:text-white"><RefreshCw className="size-4" /></Button></div>{generationRows.length === 0 ? <div className="rounded-xl border border-dashed border-white/15 p-8 text-center text-sm text-white/40">Your first recipe will appear here.</div> : <div className="space-y-2">{generationRows.map(generation => <div key={generation.id} className="rounded-lg border border-white/10 bg-[#151a1c] p-4"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-3"><span className="font-mono text-xs text-orange-300">G{String(generation.generationNumber).padStart(3, "0")}</span><span className="text-sm">Two-input split screen</span></div><span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-white/55"><StatusDot status={generation.renderStatus} />{generation.renderStatus}</span></div><div className="mt-3 flex flex-wrap gap-2 text-[11px] text-white/40"><span className="rounded bg-white/5 px-2 py-1">{generation.inputRefs.length} inputs</span><span className="rounded bg-white/5 px-2 py-1">lineage saved</span><span className="rounded bg-white/5 px-2 py-1">recipe v{generation.recipe.schema_version}</span></div></div>)}</div>}</section>
        </main>
        <aside className="border-t border-white/10 p-4 sm:p-8 lg:border-l lg:border-t-0"><div className="rounded-xl border border-cyan-300/15 bg-cyan-300/5 p-4"><div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-200"><Link2 className="size-3" /> Shared foundation</div><p className="mt-3 text-sm leading-6 text-white/70">Same IDs, recipes, hashes, and lineage contract as the Android Termux edition.</p><Separator className="my-4 bg-white/10" /><div className="space-y-3 text-xs"><div className="flex items-start gap-2"><Check className="mt-0.5 size-3 text-emerald-300" /><span className="text-white/60">Project records persist online</span></div><div className="flex items-start gap-2"><Check className="mt-0.5 size-3 text-emerald-300" /><span className="text-white/60">Recipes are Termux-portable</span></div><div className="flex items-start gap-2"><LockKeyhole className="mt-0.5 size-3 text-orange-300" /><span className="text-white/60">Media runtime is intentionally explicit</span></div></div></div><div className="mt-4 rounded-xl border border-white/10 bg-[#151a1c] p-4"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/35">When offline</p><p className="mt-2 text-sm leading-6 text-white/55">Open Termux on your phone for local FFmpeg rendering. This web app will not pretend a sleeping or disconnected phone is processing a job.</p></div></aside>
      </div>
    </div>
  );
}

function SourceCard({ label, source, sources, selected, onSelect, gain, onGain, muted, onMuted, accent }: { label: string; source?: { originalName: string; durationMs: number | null; sha256: string; status: string }; sources: Array<{ id: number; originalName: string; durationMs: number | null; status: string }>; selected?: number; onSelect: (id: number | undefined) => void; gain: number; onGain: (value: number) => void; muted: boolean; onMuted: (value: boolean) => void; accent: "cyan" | "orange" }) {
  return <div className="rounded-lg border border-white/10 bg-[#131819] p-4"><div className="mb-4 flex items-center justify-between"><div className={`flex size-8 items-center justify-center rounded-md ${accent === "cyan" ? "bg-cyan-300/10 text-cyan-200" : "bg-orange-300/10 text-orange-200"} font-mono text-sm`}>{label}</div><span className="font-mono text-[10px] uppercase tracking-wider text-white/35">input {label}</span></div><Label className="text-xs text-white/50">Registered source</Label><select value={selected ?? ""} onChange={event => onSelect(event.target.value ? Number(event.target.value) : undefined)} className="mt-2 h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 text-sm text-white outline-none focus:border-cyan-300/50"><option value="">Choose a source</option>{sources.map(item => <option key={item.id} value={item.id}>{item.originalName}</option>)}</select>{source ? <div className="mt-4 space-y-3 text-xs text-white/45"><div className="flex justify-between"><span>Duration</span><span className="font-mono text-white/75">{formatDuration(source.durationMs)}</span></div><div className="flex justify-between"><span>Integrity</span><span className="flex items-center gap-1 text-emerald-300"><Check className="size-3" /> {source.status}</span></div><div><div className="mb-1 flex justify-between"><span>Audio gain</span><span className="font-mono text-white/75">{gain.toFixed(2)}×</span></div><input aria-label={`Input ${label} audio gain`} type="range" min="0" max="2" step="0.05" value={gain} onChange={event => onGain(Number(event.target.value))} className="w-full accent-cyan-300" /></div><label className="flex items-center gap-2 text-white/55"><input type="checkbox" checked={muted} onChange={event => onMuted(event.target.checked)} /> Mute this input</label><div className="truncate font-mono text-[10px] text-white/30">{source.sha256}</div></div> : <p className="mt-5 text-xs text-white/30">Source metadata and hash will appear here.</p>}</div>;
}
