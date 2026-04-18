#!/usr/bin/env bash

input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // "Claude"')
session_name=$(echo "$input" | jq -r '.session_name // ""')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0')
cost_usd=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
lines_added=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_removed=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // 0')
cache_read=$(echo "$input" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
cache_create=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
input_tokens=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0')

used_int=$(printf "%.0f" "$used_pct")

# Build 10-character visual context bar
filled=$((used_int / 10))
empty=$((10 - filled))
bar=""
for ((i = 0; i < filled; i++)); do bar+="█"; done
for ((i = 0; i < empty; i++)); do bar+="░"; done

# Format context window size (e.g. 200k, 1M)
if [ "$ctx_size" -ge 1000000 ]; then
    ctx_fmt=$(echo "$ctx_size" | awk '{printf "%.0fM", $1 / 1000000}')
elif [ "$ctx_size" -ge 1000 ]; then
    ctx_fmt=$(echo "$ctx_size" | awk '{printf "%.0fk", $1 / 1000}')
else
    ctx_fmt="${ctx_size}"
fi

# Color-code: green <70%, yellow 70-89%, red 90%+
if [ "$used_int" -ge 90 ]; then
    color="\033[31m"
elif [ "$used_int" -ge 70 ]; then
    color="\033[33m"
else
    color="\033[32m"
fi
reset="\033[0m"

# Format cost display
cost_fmt=$(printf '$%.2f' "$cost_usd")

# Format session duration
duration_s=$((duration_ms / 1000))
if [ "$duration_s" -ge 3600 ]; then
    duration_fmt=$(printf '%dh%dm' $((duration_s / 3600)) $(((duration_s % 3600) / 60)))
elif [ "$duration_s" -ge 60 ]; then
    duration_fmt=$(printf '%dm' $((duration_s / 60)))
else
    duration_fmt="${duration_s}s"
fi

# Diff counter (only show if there are changes)
if [ "$lines_added" -gt 0 ] || [ "$lines_removed" -gt 0 ]; then
    diff_fmt="+${lines_added}/-${lines_removed}"
else
    diff_fmt=""
fi

# Cache efficiency: cache_read / (input + cache_create + cache_read)
total_tokens=$((input_tokens + cache_create + cache_read))
if [ "$total_tokens" -gt 0 ]; then
    cache_pct=$(echo "$cache_read $total_tokens" | awk '{printf "%.0f", $1 / $2 * 100}')
    cache_fmt="cache:${cache_pct}%"
else
    cache_fmt=""
fi

# Get current branch name
branch=$(git -C "$CLAUDE_PROJECT_DIR" branch --show-current 2>/dev/null || echo "detached")

# Assemble optional segments
extras=""
[ -n "$diff_fmt" ] && extras="${extras} ${diff_fmt}"
[ -n "$cache_fmt" ] && extras="${extras} ${cache_fmt}"

# Session name prefix (only when set)
if [ -n "$session_name" ]; then
    session_fmt="[${session_name}] "
else
    session_fmt=""
fi

echo -e "${session_fmt}$model | ${color}${bar} ${used_int}%/${ctx_fmt} ${cost_fmt}${reset} | ${duration_fmt}${extras} | $branch"
