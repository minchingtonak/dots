/**
 * Thinking Peek Extension (v3 — widget-based, persists final trace)
 *
 * While the model reasons, shows a live "peek" above the editor:
 *
 *   ⠹ thinking… the config in settings.json for the spinner interval
 *
 * The spinner stops as soon as the thinking phase ends (text or tool calls
 * start streaming) while the label + final trace remain. When the message
 * finishes, the tail of the final reasoning trace stays put (static) so you
 * can read what the last thought was. The line clears on the next turn.
 *
 * Rendered as a widget above the editor, NOT inside the chat:
 * - Collapsed thinking blocks keep pi's default label (setHiddenThinkingLabel
 *   is global and mutates every collapsed block incl. history).
 * - The chat region is never re-laid-out while animating, so scrolling works.
 *
 * Fits the available terminal width: the tail is truncated with a leading
 * ellipsis so the widget stays a single line. /thinking-peek <chars> caps the
 * tail below the available width if you want it shorter.
 *
 * Commands:
 *   /thinking-peek          Toggle the live peek on/off
 *   /thinking-peek <chars>  Cap tail length in chars (0 = label only, max 300)
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const WIDGET_KEY = "thinking-peek";
const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
const SPINNER_INTERVAL_MS = 120;
const DEFAULT_TAIL_CHARS = 300; // upper cap; terminal width is the effective limit
const WIDGET_LABEL = "thinking…";
const WIDGET_WIDTH_MARGIN = 6; // widget padding + safety

/** Collapse whitespace and keep the last `maxChars` code points, with a leading ellipsis. */
function collapseTail(text: string, maxChars: number): string {
	const collapsed = text.replace(/\s+/g, " ").trim();
	if (!collapsed || maxChars === 0) return "";
	const chars = Array.from(collapsed);
	if (chars.length <= maxChars) return collapsed;
	return "…" + chars.slice(chars.length - maxChars).join("");
}

/** Tail of the last non-empty thinking block in a streaming assistant message. */
function latestThinkingTail(message: { content: Array<{ type: string; thinking?: unknown }> }): string {
	let tail = "";
	for (const block of message.content) {
		if (block.type === "thinking" && typeof block.thinking === "string" && block.thinking.trim()) {
			tail = block.thinking;
		}
	}
	return tail;
}

export default function (pi: ExtensionAPI) {
	let peekEnabled = true;
	let tailChars = DEFAULT_TAIL_CHARS;

	let timer: ReturnType<typeof setInterval> | null = null;
	let frameIndex = 0;
	let tail = "";

	function stopTimer() {
		if (timer) {
			clearInterval(timer);
			timer = null;
		}
		frameIndex = 0;
	}

	function clearWidget(ctx: ExtensionContext) {
		if (ctx.hasUI) ctx.ui.setWidget(WIDGET_KEY, undefined);
	}

	/** Wipe everything: timer, state, widget. Used on new turns, disable, shutdown. */
	function reset(ctx: ExtensionContext) {
		stopTimer();
		tail = "";
		clearWidget(ctx);
	}

	function canRender(ctx: ExtensionContext): boolean {
		return peekEnabled && ctx.mode === "tui" && ctx.hasUI;
	}

	/** Draw the widget line. `frame` is the spinner char, or null for the settled state. */
	function render(ctx: ExtensionContext, frame: string | null) {
		if (!canRender(ctx)) return;
		const theme = ctx.ui.theme;
		const label = theme.fg("dim", WIDGET_LABEL);
		// Fit to one line: terminal width minus prefix, padding, and safety margin.
		const prefixLen = frame === null ? WIDGET_LABEL.length + 1 : frame.length + 1 + WIDGET_LABEL.length + 1;
		const widthFit = Math.max(0, (process.stdout.columns ?? 80) - WIDGET_WIDTH_MARGIN - prefixLen);
		const maxTail = tailChars === 0 ? 0 : Math.min(tailChars, widthFit);
		const tailText = collapseTail(tail, maxTail);
		const line =
			frame === null
				? tailText
					? `${label} ${theme.italic(theme.fg("thinkingText", tailText))}`
					: `${label}`
				: tailText
					? `${theme.fg("accent", frame)} ${label} ${theme.italic(theme.fg("thinkingText", tailText))}`
					: `${theme.fg("accent", frame)} ${label}`;
		ctx.ui.setWidget(WIDGET_KEY, [line]);
	}

	/** Message finished: stop the spinner, keep the label + final tail.
	 * No trace (message never thought) -> clear the widget entirely so a
	 * bare "thinking…" label isn't left hanging above the editor. */
	function finalize(ctx: ExtensionContext) {
		stopTimer();
		if (tail.trim()) {
			render(ctx, null);
		} else {
			clearWidget(ctx);
		}
	}

	function tick(ctx: ExtensionContext) {
		render(ctx, SPINNER_FRAMES[frameIndex % SPINNER_FRAMES.length] ?? "⠿");
		frameIndex++;
	}

	function start(ctx: ExtensionContext) {
		if (timer || !canRender(ctx)) return;
		tick(ctx);
		timer = setInterval(() => tick(ctx), SPINNER_INTERVAL_MS);
	}

	// New user turn -> fresh slate (old trace stays readable until now).
	pi.on("agent_start", async (_event, ctx) => {
		reset(ctx);
	});

	// Per-message freshness within a multi-message (tool-call) run.
	pi.on("message_start", async (event, ctx) => {
		if (event.message.role === "assistant") {
			stopTimer();
			tail = "";
		}
	});

	pi.on("message_update", async (event, ctx) => {
		if (!peekEnabled || ctx.mode !== "tui") return;
		if (event.message.role !== "assistant") return;
		// Only animate while reasoning tokens are actively streaming in.
		const streamEvent = event.assistantMessageEvent;
		if (!streamEvent) return;

		switch (streamEvent.type) {
			case "thinking_delta":
				// Reasoning tokens streaming in -> animate.
				tail = latestThinkingTail(event.message) || tail;
				start(ctx);
				break;
			case "thinking_end":
				// Authoritative final content for this thinking block.
				if (typeof streamEvent.content === "string" && streamEvent.content.trim()) {
					tail = streamEvent.content;
				}
				finalize(ctx);
				break;
			case "text_start":
			case "toolcall_start":
				// Thinking phase is over -> stop the spinner, keep the trace.
				finalize(ctx);
				break;
		}
	});

	// Assistant message done -> spinner stops, final trace stays.
	pi.on("message_end", async (event, ctx) => {
		if (event.message.role !== "assistant") return;
		const finalTail = latestThinkingTail(event.message);
		if (finalTail) tail = finalTail;
		finalize(ctx);
	});

	// Run over (incl. aborts): make sure the spinner stopped; keep final trace.
	pi.on("agent_end", async (_event, ctx) => {
		finalize(ctx);
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		reset(ctx);
	});

	pi.registerCommand("thinking-peek", {
		description: "Toggle live thinking peek, or cap tail length in chars (0 = label only)",
		handler: async (args, ctx) => {
			const trimmed = args.trim();

			if (!trimmed) {
				peekEnabled = !peekEnabled;
				if (!peekEnabled) reset(ctx);
				ctx.ui.notify(`Thinking peek: ${peekEnabled ? "on" : "off"}`, "info");
				return;
			}

			const parsed = Number.parseInt(trimmed, 10);
			if (Number.isNaN(parsed) || parsed < 0 || parsed > 300) {
				ctx.ui.notify("Usage: /thinking-peek [0-300 tail chars]", "error");
				return;
			}
			tailChars = parsed;
			ctx.ui.notify(`Thinking peek tail length: ${tailChars} chars`, "info");
		},
	});
}
