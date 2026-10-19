# herdr-plugin-claude-restart

Claude Code 업데이트 후 herdr 안의 Claude 창을 한 번에 새 버전으로 올린다.

대기(idle) 중인 Claude 창마다 `/exit` → 같은 창에서 `claude --resume <세션ID>` 로 다시 띄운다. 대화는 그대로 이어진다.
작업 중(working)·승인 대기(blocked) 창은 건드리지 않는다.

## 설치

```sh
herdr plugin link /Users/jerry.axz-pc/Projects/herdr-plugin/herdr-plugin-claude-restart
```

`~/.config/herdr/config.toml` 단축키:

```toml
[[keys.command]]
key = "prefix+r"
type = "plugin_action"
command = "claude-restart.restart-all"
description = "restart idle claude panes"
```

수동 실행: `herdr plugin action claude-restart.restart-all`

## 한계

- herdr가 세션 ID를 모르는 창(`agent_session` 없음)은 건너뛴다.
- 백그라운드 세션은 대상이 아니다. `claude respawn --all` 을 쓴다.
