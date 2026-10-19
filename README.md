# herdr-plugin-agent-restart

Claude Code 업데이트 후 herdr 안의 Claude 창을 한 번에 새 버전으로 올린다.

대기(idle) 중이고 **이전 버전으로 떠 있는** Claude 창마다 프로세스를 종료(SIGTERM)하고, 그 창에 열려 있던 세션을 같은 창에서 `claude --resume <세션ID>` 로 다시 연다.

- 세션 ID는 herdr 값이 아니라 Claude 프로세스의 `~/.claude/sessions/<pid>.json` 에서 읽는다 (`/clear` 후에도 정확).
- 대화가 없는 빈 세션은 `claude` 로 새로 띄운다.
- 이미 최신 버전인 창, 작업 중(working)·승인 대기(blocked) 창은 건드리지 않는다.
- 입력창에 쓰다 만 초안은 사라진다.

## 설치

```sh
herdr plugin link /Users/jerry.axz-pc/Projects/herdr-plugin/herdr-plugin-agent-restart
```

`~/.config/herdr/config.toml` 단축키:

```toml
[[keys.command]]
key = "prefix+r"
type = "plugin_action"
command = "agent-restart.restart-all"
description = "restart idle claude panes"
```

수동 실행: `herdr plugin action agent-restart.restart-all`

한 창만: `sh scripts/restart-all.sh <pane_id>`

## 한계

- 백그라운드 세션은 대상이 아니다. `claude respawn --all` 을 쓴다.
