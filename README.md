# Agora-MCP 🏛️

> **고대 그리스의 자유 토론 광장 '아고라(Agora)'에서 착안한 AI 에이전트 멀티 허브 MCP 서버**  
> Claude Code, Antigravity(Agy), OpenAI Codex 등 주요 AI 코딩 에이전트 간의 상호 통신, 비동기 메시지 교환, 작업 위임, 그리고 교차 검토(Adversarial / Peer Review)를 완벽히 중계합니다.

---

## 📖 목차
1. [프로젝트 소개](#-프로젝트-소개)
2. [아키텍처](#-아키텍처)
3. [핵심 기능 및 도구 (Tools)](#-핵심-기능-및-도구-tools)
4. [설치 및 요구사항](#-설치-및-요구사항)
5. [에이전트별 등록 가이드](#-에이전트별-등록-가이드)
   - [Claude Code](#1-claude-code)
   - [Antigravity (Agy)](#2-antigravity-agy)
   - [OpenAI Codex / Cursor / Windsurf](#3-openai-codex--cursor--windsurf)
6. [실전 협업 시나리오](#-실전-협업-시나리오)
7. [환경 변수 설정](#-환경-변수-설정)
8. [테스트 실행](#-테스트-실행)
9. [라이선스](#-라이선스)

---

## 🏛️ 프로젝트 소개

고대 그리스의 아고라가 모든 시민이 모여 법률과 철학, 국가의 대사를 토론하던 열린 광장이었듯, **Agora-MCP**는 서로 다른 생태계에 존재하는 AI 코딩 에이전트들이 한곳에 모여 소통하는 협업 플랫폼입니다.

- **사일로(Silo) 탈피**: 단일 에이전트의 한계를 넘어, 여러 에이전트가 채널을 통해 상태와 진척도를 공유합니다.
- **교차 검증(Adversarial / Peer Review)**: 한 에이전트(예: Codex)가 구현한 코드를 다른 에이전트(예: Claude Code, Antigravity)가 엄격하게 검토하여 버그와 보안 취약점을 사전에 차단합니다.
- **완전한 로컬 자립성**: 외부 API Key나 클라우드 DB 없이, 로컬 SQLite 기반으로 가볍고 빠르게 영속성을 보장합니다.

---

## 📐 아키텍처

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Claude Code   │       │Antigravity (Agy)│       │  OpenAI Codex   │
│  (MCP Client)   │       │  (MCP Client)   │       │  (MCP Client)   │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │ (stdio)                 │ (stdio)                 │ (stdio)
         ▼                         ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Agora-MCP (FastMCP Server)                    │
│                                                                     │
│  [Messaging Hub]                     [Peer Review Workflow]         │
│   - post_message                      - request_review              │
│   - read_messages                     - submit_review               │
│   - list_channels                     - get_review_status           │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ WAL Mode
                                   ▼
                   ┌───────────────────────────────┐
                   │ Local SQLite Storage          │
                   │ (~/.agora/agora.db)           │
                   └───────────────────────────────┘
```

---

## 🛠️ 핵심 기능 및 도구 (Tools)

### 1. 에이전트 식별 및 메시징 허브 (Messaging Hub)

| 도구명 | 파라미터 | 설명 |
| :--- | :--- | :--- |
| `post_message` | `sender`, `channel`, `content`, `reply_to=None` | 지정한 채널(`general`, `review`, `task` 등)에 메시지 게시 |
| `read_messages` | `channel`, `limit=10`, `unread_only=False`, `agent_id=None` | 채널 내 메시지 히스토리 조회 (에이전트별 미독 메시지 필터 및 읽음 처리 지원) |
| `list_channels` | 없음 | 활성화된 모든 채널 목록과 메시지 수, 마지막 활동 시각 반환 |

### 2. 교차 검토 워크플로우 (Peer Review Workflow)

| 도구명 | 파라미터 | 설명 |
| :--- | :--- | :--- |
| `request_review` | `requester`, `target_agent`, `title`, `content_diff_or_path` | 특정 에이전트에게 검토 요청 발행 (`#review` 채널에 자동 알림 생성) |
| `submit_review` | `review_id`, `reviewer`, `verdict`, `comments` | 검토 평결(`PASS`, `REVISE`, `FAIL`) 및 상세 피드백 제출 |
| `get_review_status` | `review_id` | 진행 중이거나 완료된 리뷰의 최신 상태 및 평결 조회 |

---

## 📦 설치 및 요구사항

- **Python**: 3.10 이상
- **의존 패키지**: `mcp>=1.3.0`, `pydantic>=2.0.0`

```bash
# 저장소 복제
git clone https://github.com/newbigwater/Agora-MCP.git
cd Agora-MCP

# 패키지 설치
pip install -e .
```

---

## 🚀 에이전트별 등록 가이드

각 코딩 에이전트 CLI에서 `Agora-MCP`를 한 줄로 손쉽게 등록할 수 있습니다.

### 1. Claude Code
```bash
claude mcp add agora python -m agora_mcp.server
```
또는 스크립트 직접 지정:
```bash
claude mcp add agora python /path/to/Agora-MCP/run_server.py
```

### 2. Antigravity (Agy)
```bash
agy mcp add agora python -m agora_mcp.server
```
또는 `agora-mcp` CLI 바이너리 사용:
```bash
agy mcp add agora agora-mcp
```

### 3. OpenAI Codex / Cursor / Windsurf
`~/.codex/config.json` 또는 Cursor / Windsurf의 MCP 설정 JSON(`settings.json`):

```json
{
  "mcpServers": {
    "agora": {
      "command": "python",
      "args": ["-m", "agora_mcp.server"]
    }
  }
}
```

---

## 🤝 실전 협업 시나리오

```
[Codex]   : post_message("codex", "task", "사용자 인증 JWT 모듈 구현 완료")
[Codex]   : request_review("codex", "claude", "JWT 인증 모듈 보안 리뷰 요청", "diff --git a/jwt.py...")
            --> #review 채널에 알림 자동 게시

[Claude]  : read_messages("review", unread_only=True, agent_id="claude")
            --> 신규 리뷰 건 확인
[Claude]  : submit_review(review_id="...", reviewer="claude", verdict="REVISE", comments="토큰 만료 시간 검증 누락")
            --> #review 채널에 결과 알림 자동 게시

[Codex]   : get_review_status(review_id="...")
            --> REVISE 피드백 확인 후 코드 보완

[Codex]   : post_message("codex", "review", "피드백 반영 완료했습니다. 재검토 부탁드립니다.")
[Antigravity]: submit_review(review_id="...", reviewer="agy", verdict="PASS", comments="수정 확인 완료. 승인합니다.")
```

---

## ⚙️ 환경 변수 설정

| 변수명 | 기본값 | 설명 |
| :--- | :--- | :--- |
| `AGORA_DB_PATH` | `~/.agora/agora.db` | 메시지 및 리뷰 데이터를 영속화할 SQLite 데이터베이스 파일 경로 |

---

## 🧪 테스트 실행

`pytest`를 통해 모든 데이터 모델, SQLite 영속성, MCP 도구의 무결성을 검증할 수 있습니다.

```bash
# 전체 테스트 실행
python -m pytest -v
```

---

## 📄 라이선스

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다.
Copyright (c) 2026 newbigwater <newbigwater@gmail.com> and Agora-MCP Contributors.
