/**
 * vision-delegate.ts
 *
 * Seamless vision delegation for text-only main models (e.g. zai/glm-5.3):
 *
 * 1. `before_agent_start`: when the active model cannot view images, every image
 *    reachable from the prompt — attached blocks AND local image file paths
 *    mentioned in the text (pi's TUI paste inserts paths without attaching) —
 *    is described by zai/glm-5.3-flash with a question-aware prompt, and the
 *    descriptions are injected as a custom message.
 * 2. `input`: when the active model CAN view images, local image paths in the
 *    prompt text are attached as real image blocks (works around the TUI never
 *    attaching pasted images interactively).
 *
 * - Original images/paths stay visible in the transcript; descriptions persist
 *   in the session and survive compaction.
 * - No-op when there is nothing to delegate. On flash failure, falls back to
 *   pi's default placeholder behavior.
 */

import { readFile, stat } from "node:fs/promises";
import { isAbsolute, resolve as resolvePath } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { ImageContent, Model, Usage } from "@earendil-works/pi-ai";
import { uuidv7 } from "@earendil-works/pi-ai";

const VISION_PROVIDER = "zai";
const VISION_MODEL_ID = "glm-5.3-flash";
const MAX_PROMPT_CONTEXT_CHARS = 1500;
const MAX_IMAGES_PER_PROMPT = 4;
const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const DESCRIPTION_CACHE_LIMIT = 32;

const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "gif", "webp", "bmp"]);
const MIME_BY_EXT: Record<string, string> = {
	png: "image/png",
	jpg: "image/jpeg",
	jpeg: "image/jpeg",
	gif: "image/gif",
	webp: "image/webp",
	bmp: "image/bmp",
};

type ExtensionCtx = Parameters<Parameters<ExtensionAPI["on"]>[1]>[1];

interface CandidateImage {
	image: ImageContent;
	label: string;
	cacheKey: string;
}

interface DescriptionResult {
	description?: string;
	error?: string;
	usage?: Usage;
}

function hashString(s: string): string {
	let h = 5381;
	for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
	return h.toString(36);
}

/** Extract plausible local image file paths mentioned in prompt text. */
function extractImagePathTokens(prompt: string): string[] {
	const tokens: string[] = [];
	for (const raw of prompt.split(/\s+/)) {
		let t = raw.replace(/^[([{<" '`]+/, "").replace(/[)\]}>" '`,]+$/, "");
		if (t.startsWith("@")) t = t.slice(1);
		if (!t || t.startsWith("http://") || t.startsWith("https://") || t.startsWith("/")) continue;
		if (t.startsWith("/")) t = t; // absolute path (kept after url check)
		const ext = t.split(".").pop()?.toLowerCase() ?? "";
		if (!IMAGE_EXTENSIONS.has(ext)) continue;
		tokens.push(t);
	}
	return [...new Set(tokens)].slice(0, MAX_IMAGES_PER_PROMPT);
}

async function loadImageFile(absPath: string): Promise<{ image: ImageContent; mtimeMs: number } | undefined> {
	try {
		const st = await stat(absPath);
		if (!st.isFile() || st.size === 0 || st.size > MAX_IMAGE_BYTES) return undefined;
		const ext = absPath.split(".").pop()?.toLowerCase() ?? "";
		const data = (await readFile(absPath)).toString("base64");
		return { image: { type: "image", data, mimeType: MIME_BY_EXT[ext] ?? "image/png" }, mtimeMs: st.mtimeMs };
	} catch {
		return undefined;
	}
}

/** Load candidate images: prompt-text paths + any attached image blocks, deduped by content. */
async function collectCandidates(prompt: string, attachments: ImageContent[], cwd: string): Promise<CandidateImage[]> {
	const candidates: CandidateImage[] = [];
	const seen = new Set<string>();
	const promptHash = hashString(prompt);

	const add = (image: ImageContent, label: string, cacheKey: string) => {
		const dedupe = `${image.mimeType}:${image.data.length}:${hashString(image.data)}`;
		if (seen.has(dedupe)) return;
		seen.add(dedupe);
		candidates.push({ image, label, cacheKey });
	};

	// Attached image blocks first (explicit user intent).
	attachments.slice(0, MAX_IMAGES_PER_PROMPT).forEach((image, i) =>
		add(image, `attachment ${i + 1}`, `attach:${dedupeKey(image)}:${promptHash}`),
	);

	// Image paths mentioned in the text (pi TUI paste / typed paths are never attached).
	if (candidates.length < MAX_IMAGES_PER_PROMPT) {
		for (const token of extractImagePathTokens(prompt)) {
			if (candidates.length >= MAX_IMAGES_PER_PROMPT) break;
			const abs = isAbsolute(token) ? token : resolvePath(cwd, token);
			const loaded = await loadImageFile(abs);
			if (loaded) add(loaded.image, abs, `file:${abs}:${loaded.mtimeMs}:${promptHash}`);
		}
	}

	return candidates;
}

function dedupeKey(image: ImageContent): string {
	return `${image.mimeType}:${image.data.length}:${hashString(image.data)}`;
}

function buildDescriptionPrompt(userPrompt: string, label: string, index: number, total: number): string {
	const which = total > 1 ? ` (image ${index + 1} of ${total})` : "";
	const source = label.startsWith("attachment") ? "" : `\nThe image comes from the file: ${label}`;
	const question = userPrompt.trim()
		? `\n\nThe user's message accompanying this image is:\n"""\n${userPrompt.slice(0, MAX_PROMPT_CONTEXT_CHARS)}${userPrompt.length > MAX_PROMPT_CONTEXT_CHARS ? "\n…" : ""}\n"""`
		: "";

	return (
		[
			`You are acting as the eyes for a text-only AI coding assistant. The user supplied an image${which} that the main assistant cannot see.`,
			"Describe it so the main assistant can work with it without seeing it. Include:",
			"- What kind of image it is (screenshot, photo, diagram, chart, UI, error dialog, code, ...)",
			"- ALL visible text transcribed verbatim: error messages, labels, code, filenames, values",
			"- Layout, key objects, and relevant colors or styling",
			"- Anything specifically relevant to answering the user's message",
			"",
			"Be precise and factual; do not speculate beyond what is visible. Reply with the description only (markdown), no preamble.",
		].join("\n") + source + question
	);
}

const descriptionCache = new Map<string, DescriptionResult>();

async function describeImage(
	ctx: ExtensionCtx,
	visionModel: Model,
	candidate: CandidateImage,
	userPrompt: string,
	index: number,
	total: number,
): Promise<DescriptionResult> {
	const cached = descriptionCache.get(candidate.cacheKey);
	if (cached) return cached;

	try {
		const response = await ctx.modelRegistry.complete(
			visionModel,
			{
				messages: [
					{
						role: "user",
						content: [
							{ type: "text", text: buildDescriptionPrompt(userPrompt, candidate.label, index, total) },
							{ type: "image", data: candidate.image.data, mimeType: candidate.image.mimeType },
						],
						timestamp: Date.now(),
					},
				],
			},
			{
				maxTokens: 4096,
				cacheRetention: "none",
				sessionId: uuidv7(),
				signal: ctx.signal,
			},
		);

		if (response.stopReason === "error" || response.stopReason === "aborted") {
			return { error: response.errorMessage ?? `stopReason: ${response.stopReason}` };
		}

		const description = response.content
			.filter((c): c is { type: "text"; text: string } => c.type === "text")
			.map((c) => c.text)
			.join("\n")
			.trim();

		const result: DescriptionResult = description
			? { description, usage: response.usage }
			: { error: "empty description", usage: response.usage };

		descriptionCache.set(candidate.cacheKey, result);
		if (descriptionCache.size > DESCRIPTION_CACHE_LIMIT) {
			const oldest = descriptionCache.keys().next().value;
			if (oldest !== undefined) descriptionCache.delete(oldest);
		}
		return result;
	} catch (error) {
		return { error: error instanceof Error ? error.message : String(error) };
	}
}

export default function (pi: ExtensionAPI) {
	// Vision-capable main model: attach local image paths found in prompt text.
	pi.on("input", async (event, ctx) => {
		if (event.source === "extension") return { action: "continue" };
		const model = ctx.model;
		if (!model || !model.input.includes("image")) return { action: "continue" }; // described in before_agent_start instead
		const text = event.text;
		if (!text || text.startsWith("/") || text.startsWith("!")) return { action: "continue" };
		if (event.images?.length) return { action: "continue" };

		const tokens = extractImagePathTokens(text);
		if (tokens.length === 0) return { action: "continue" };

		const images: ImageContent[] = [];
		for (const token of tokens) {
			const abs = isAbsolute(token) ? token : resolvePath(ctx.cwd, token);
			const loaded = await loadImageFile(abs);
			if (loaded) images.push(loaded.image);
		}
		if (images.length === 0) return { action: "continue" };

		return { action: "transform", text, images };
	});

	// Text-only main model: describe all reachable images via the vision model.
	pi.on("before_agent_start", async (event, ctx) => {
		const activeModel = ctx.model;
		if (!activeModel || activeModel.input.includes("image")) return;

		const candidates = await collectCandidates(event.prompt, event.images ?? [], ctx.cwd);
		if (candidates.length === 0) return;

		const visionModel = ctx.modelRegistry.find(VISION_PROVIDER, VISION_MODEL_ID);
		if (!visionModel || !visionModel.input.includes("image")) {
			ctx.ui.notify(
				`vision-delegate: vision model ${VISION_PROVIDER}/${VISION_MODEL_ID} not found; images will be omitted`,
				"warning",
			);
			return;
		}
		if (!ctx.modelRegistry.hasConfiguredAuth(visionModel)) {
			ctx.ui.notify(`vision-delegate: no auth for ${VISION_PROVIDER}, images will be omitted`, "warning");
			return;
		}

		ctx.ui.setStatus(
			"vision",
			`describing ${candidates.length} image${candidates.length > 1 ? "s" : ""} with ${VISION_MODEL_ID}…`,
		);

		const results = await Promise.all(
			candidates.map((candidate, i) =>
				describeImage(ctx, visionModel, candidate, event.prompt, i, candidates.length),
			),
		);

		ctx.ui.setStatus("vision", undefined);

		const ok = results.filter((r): r is DescriptionResult => !!r?.description);
		if (ok.length === 0) {
			ctx.ui.notify(`vision-delegate: image description failed (${results[0]?.error ?? "unknown error"})`, "error");
			return;
		}

		const parts = candidates.map((candidate, i) => {
			const header = `### ${candidate.label}`;
			const body = results[i]?.description ?? `(Description failed: ${results[i]?.error ?? "unknown error"})`;
			return `${header}\n${body}`;
		});

		const usage: Usage[] = ok.map((r) => r.usage).filter((u): u is Usage => !!u);
		const totalTokens = usage.reduce((sum, u) => sum + (u.input + u.output + u.cacheRead + u.cacheWrite), 0);

		return {
			message: {
				customType: "vision-delegate",
				display: true,
				content:
					`[vision-delegate] The active model (${activeModel.id}) cannot view images. ` +
					`${VISION_PROVIDER}/${VISION_MODEL_ID} described the image${candidates.length > 1 ? "s" : ""} below ` +
					`(${totalTokens.toLocaleString()} nested tokens). Treat these descriptions as an accurate account of ` +
					`the image contents; rely on them instead of analyzing image files yourself:\n\n` +
					parts.join("\n\n"),
				details: {
					visionModel: `${VISION_PROVIDER}/${VISION_MODEL_ID}`,
					imageCount: candidates.length,
					nestedUsage: usage,
				},
			},
		};
	});
}
