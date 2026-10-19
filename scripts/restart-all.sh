#!/bin/sh
# Restart each idle Claude pane that runs an outdated binary and resume the session it had open.
# Working or blocked panes are skipped so no in-flight turn is cut off.
set -eu

herdr=${HERDR_BIN_PATH:-herdr}
# Plugin actions may not inherit the login PATH, so fall back to the native install path.
latest=$(basename "$(readlink "$(command -v claude || echo "$HOME/.local/bin/claude")")")
sessions=$HOME/.claude/sessions
list=${TMPDIR:-/tmp}/agent-restart.$$
trap 'rm -f "$list"' EXIT

# Optional first argument limits the run to one pane.
"$herdr" agent list | jq -r --arg only "${1:-}" '.result.agents[]
    | select(.agent == "claude" and .agent_status == "idle")
    | select($only == "" or .pane_id == $only) | .pane_id' >"$list"

done_n=0
fail_n=0
while read -r pane; do
    # The native installer names the process after its version (e.g. "2.1.303").
    info=$("$herdr" pane process-info --pane "$pane" | jq -r '.result.process_info.foreground_processes[0] | "\(.pid) \(.name)"')
    pid=${info%% *}
    version=${info#* }
    [ "$version" != "$latest" ] || continue

    # herdr's agent_session can be stale (after /clear, or a session with no messages);
    # Claude's own per-process file holds the session actually open in the pane.
    sid=$(jq -r '.sessionId // empty' "$sessions/$pid.json" 2>/dev/null || true)

    # A signal instead of typing /exit: typed text would land in a half-written draft or an open picker.
    kill -TERM "$pid" 2>/dev/null || continue
    i=0
    while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 20 ]; do
        i=$((i + 1))
        sleep 0.5
    done
    if kill -0 "$pid" 2>/dev/null; then
        fail_n=$((fail_n + 1))
        continue
    fi

    # A session with no messages has no transcript and cannot be resumed.
    if [ -n "$sid" ] && find "$HOME/.claude/projects" -maxdepth 2 -name "$sid.jsonl" | grep -q .; then
        "$herdr" pane run "$pane" "claude --resume $sid" >/dev/null
    else
        "$herdr" pane run "$pane" "claude" >/dev/null
    fi
    done_n=$((done_n + 1))
done <"$list"

body="${done_n}개 재시작 ($latest)"
[ "$fail_n" -eq 0 ] || body="$body, ${fail_n}개 종료 안 됨"
"$herdr" notification show "Agent Restart" --body "$body" >/dev/null
