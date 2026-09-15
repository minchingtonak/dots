/**
 * Status line extension — pi port of ~/.claude/statusline.sh
 *
 * Shows in the footer: model name, a colored context-usage bar, git branch,
 * turn indicator, and (for the zai provider) GLM Coding Plan quota usage.
 * Quota responses are cached for 60s; stale data is served on fetch failure.
 * Also renders a ⬆N badge when extension updates are available (see
 * update-check.mjs; cache in ~/.pi/agent/cache/extension-updates.json).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execSync, spawn } from "node:child_process";
import { readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";

const ZAI_QUOTA_URL = "https://api.z.ai/api/monitor/usage/quota/limit";
const QUOTA_TTL_MS = 60_000;

const UPDATES_CACHE = `${homedir()}/.pi/agent/cache/extension-updates.json`;
const UPDATES_MANIFEST = `${homedir()}/.pi/agent/npm/package.json`;
const UPDATES_TTL_MS = 3600_000;

let quotaCache: { at: number; text: string } | undefined;

function bar(pct: number): string {
	const filled = Math.round(pct / 10);
	return "█".repeat(filled) + "░".repeat(10 - filled);
}

function fmtTokens(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(0)}M`;
	if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
	return String(n);
}

function gitBranch(): string {
	try {
		return (
			execSync("git branch --show-current", {
				encoding: "utf8",
				timeout: 2000,
				stdio: ["ignore", "pipe", "ignore"],
			}).trim() || "detached"
		);
	} catch {
		return "";
	}
}

async function zaiQuota(ctx: any): Promise<string> {
	if (quotaCache && Date.now() - quotaCache.at < QUOTA_TTL_MS) return quotaCache.text;
	try {
		let token: string | undefined;
		try {
			token = ctx.modelRegistry.getProviderAuth("zai")?.apiKey;
		} catch {
			/* fall through */
		}
		if (!token) {
			try {
				token = JSON.parse(
					readFileSync(`${homedir()}/.pi/agent/auth.json`, "utf8"),
				).zai?.key;
			} catch {
				/* give up quietly */
			}
		}
		token ??= process.env.ZAI_API_KEY ?? process.env.ANTHROPIC_AUTH_TOKEN;
		if (!token) return "";

		const res = await fetch(ZAI_QUOTA_URL, {
			headers: { Authorization: token, "Content-Type": "application/json" },
			signal: AbortSignal.timeout(4000),
		});
		if (!res.ok) return quotaCache?.text ?? "";
		const json: any = await res.json();
		const text = (json?.data?.limits ?? [])
			.slice()
			.sort((a: any, b: any) => a.usage - b.usage)
			.map((l: any) => `${l.currentValue}/${l.usage}`)
			.join("·");
		quotaCache = { at: Date.now(), text: text ? `⚡${text}` : "" };
		return quotaCache.text;
	} catch {
		return quotaCache?.text ?? "";
	}
}

function maybeKickUpdateCheck(): void {
	// re-check hourly, or sooner after `pi update` bumps the npm manifest
	let cacheAge = Infinity;
	let manifestAge = Infinity;
	try {
		cacheAge = Date.now() - statSync(UPDATES_CACHE).mtimeMs;
	} catch {
		/* no cache yet */
	}
	try {
		manifestAge = Date.now() - statSync(UPDATES_MANIFEST).mtimeMs;
	} catch {
		/* no packages installed yet */
	}
	if (cacheAge < UPDATES_TTL_MS && cacheAge < manifestAge) return;
	try {
		spawn(process.execPath, [`${homedir()}/.pi/agent/extensions/update-check.mjs`], {
			detached: true,
			stdio: "ignore",
		}).unref();
	} catch {
		/* statusline must never break */
	}
}

function updateBadge(ctx: any): string {
	maybeKickUpdateCheck();
	try {
		const cache = JSON.parse(readFileSync(UPDATES_CACHE, "utf8"));
		const count = cache?.count ?? 0;
		if (count > 0) return ctx.ui.theme.fg("warning", `⬆${count}`);
	} catch {
		/* no cache yet */
	}
	return "";
}

async function refresh(ctx: any, spin: string, extra: string): Promise<void> {
	const theme = ctx.ui.theme;
	const parts: string[] = [];

	const model = ctx.model;
	parts.push(theme.fg("dim", model ? model.id : "no-model"));

	const usage = ctx.getContextUsage?.();
	const window =
		model?.context_window ??
		ctx.modelRegistry?.find?.(model?.provider, model?.id)?.context_window ??
		1_000_000; // zai GLM coding plan is 1M; conservative default otherwise
	if (usage && model) {
		const pct = Math.min(100, Math.round((usage.tokens / window) * 100));
		const color = pct >= 90 ? "error" : pct >= 70 ? "warning" : "success";
		parts.push(theme.fg(color, `${bar(pct)} ${pct}%/${fmtTokens(window)}`));
	}

	const branch = gitBranch();
	if (branch) parts.push(theme.fg("accent", branch));

	const badge = updateBadge(ctx);
	if (badge) parts.push(badge);

	const quota = model?.provider === "zai" ? await zaiQuota(ctx) : "";
	parts.push(spin + extra + (quota ? ` ${quota}` : ""));

	ctx.ui.setStatus("statusline", parts.join(theme.fg("dim", " | ")));
}

export default function (pi: ExtensionAPI) {
	void pi;
	let turnCount = 0;

	pi.on("session_start", async (_event, ctx) => refresh(ctx, "", "ready"));
	pi.on("turn_start", async (_event, ctx) => {
		turnCount++;
		await refresh(ctx, "◐ ", `turn ${turnCount}`);
	});
	pi.on("turn_end", async (_event, ctx) => refresh(ctx, "✓ ", `turn ${turnCount}`));
	pi.on("model_select", async (_event, ctx) => refresh(ctx, "", "ready"));
}
