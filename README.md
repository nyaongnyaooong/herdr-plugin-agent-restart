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

## Windows

Windows에서는 Python 3.9+와 PowerShell을 사용하며 Bash나 jq는 필요하지 않다. `HERDR_PYTHON`으로 Python 경로를 지정할 수 있다. `prefix+r`을 `agent-restart.restart-all-windows`에 연결한다.

실행 파일 경로의 버전 또는 최신 네이티브 바이너리 설치 시각과 프로세스 시작 시각을 비교한다. 버전을 확인할 수 없는 프로세스는 건드리지 않는다. 종료 직전 idle 상태와 프로세스 신원을 재확인하고, Windows 프로세스 API로 종료한 뒤 기존 세션을 재개한다. 강제 종료되므로 입력 중인 초안은 보존되지 않는다.

`python scripts/test_windows.py`로 버전 판별, 작업 중인 창 제외, 세션 재개 및 격리된 테스트 프로세스 종료를 검증한다.

## 한계

- 백그라운드 세션은 대상이 아니다. `claude respawn --all` 을 쓴다.
