#!/bin/sh
# /exit each idle Claude pane and resume the same session, so it runs the newly installed binary.
# Working or blocked panes are skipped so no in-flight turn is cut off.
set -eu

herdr=${HERDR_BIN_PATH:-herdr}

"$herdr" agent list | jq -r '.result.agents[]
    | select(.agent == "claude" and .agent_status == "idle" and .agent_session.value != null)
    | "\(.pane_id) \(.agent_session.value)"' >"${TMPDIR:-/tmp}/claude-restart.$$"

done_n=0
fail_n=0
while read -r pane sid; do
    "$herdr" pane send-text "$pane" "/exit" >/dev/null
    "$herdr" pane send-keys "$pane" enter >/dev/null
    # Wait up to 10s for Claude to leave the pane before typing into the shell.
    i=0
    while [ "$("$herdr" pane get "$pane" | jq -r '.result.pane.agent // empty')" = "claude" ]; do
        i=$((i + 1))
        [ "$i" -le 20 ] || break
        sleep 0.5
    done
    if [ "$i" -gt 20 ]; then
        fail_n=$((fail_n + 1))
        continue
    fi
    "$herdr" pane run "$pane" "claude --resume $sid" >/dev/null
    done_n=$((done_n + 1))
done <"${TMPDIR:-/tmp}/claude-restart.$$"
rm -f "${TMPDIR:-/tmp}/claude-restart.$$"

body="${done_n}개 재시작"
[ "$fail_n" -eq 0 ] || body="$body, ${fail_n}개 종료 안 됨"
"$herdr" notification show "Claude Restart" --body "$body" >/dev/null
