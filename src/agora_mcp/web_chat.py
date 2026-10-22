"""
Agora Web Chat UI 모듈
Starlette 기반의 경량 실시간 웹 채팅 대시보드
에이전트(Codex, Agy, Claude)와 인간(User) 간의 대화를 실시간으로 모니터링하고 직접 대화에 참여할 수 있습니다.
"""
import json
import sqlite3
from typing import Optional
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from agora_mcp.storage import AgoraStorage

_storage: Optional[AgoraStorage] = None


def get_storage() -> AgoraStorage:
    """현재 스토리지 인스턴스 반환"""
    global _storage
    if _storage is None:
        _storage = AgoraStorage()
        _storage.init_db()
    return _storage


def set_storage(storage: AgoraStorage) -> None:
    """테스트용 스토리지 주입"""
    global _storage
    _storage = storage


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agora Chat Hub 🏛️</title>
    <style>
        :root {
            --bg-dark: #1e1f22;
            --bg-sidebar: #2b2d31;
            --bg-chat: #313338;
            --bg-card: #383a40;
            --text-normal: #dbdee1;
            --text-muted: #949ba4;
            --accent-primary: #5865f2;
            --accent-green: #23a55a;
            --accent-amber: #f0b232;
            --accent-red: #f23f43;
            --border-color: #3f4147;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-normal);
            height: 100vh;
            display: flex;
            overflow: hidden;
        }
        /* 사이드바 */
        #sidebar {
            width: 260px;
            background-color: var(--bg-sidebar);
            display: flex;
            flex-direction: column;
            border-right: 1px solid var(--border-color);
        }
        .sidebar-header {
            padding: 16px;
            font-size: 1.1rem;
            font-weight: 700;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .channel-list {
            padding: 12px 8px;
            flex: 1;
            overflow-y: auto;
        }
        .channel-section-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            font-weight: 700;
            color: var(--text-muted);
            padding: 8px 8px 4px;
        }
        .channel-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            margin-bottom: 2px;
            border-radius: 6px;
            cursor: pointer;
            color: var(--text-muted);
            font-size: 0.95rem;
            transition: background 0.15s, color 0.15s;
        }
        .channel-item:hover {
            background-color: rgba(255, 255, 255, 0.05);
            color: var(--text-normal);
        }
        .channel-item.active {
            background-color: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-weight: 600;
        }
        .channel-badge {
            background-color: var(--bg-card);
            font-size: 0.75rem;
            padding: 2px 6px;
            border-radius: 10px;
            color: var(--text-muted);
        }
        /* 메인 채팅 영역 */
        #chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background-color: var(--bg-chat);
        }
        .chat-header {
            padding: 14px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: var(--bg-chat);
        }
        .chat-title {
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .review-banner {
            background-color: var(--bg-card);
            padding: 10px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            gap: 12px;
            overflow-x: auto;
            font-size: 0.85rem;
        }
        .review-card {
            background-color: var(--bg-sidebar);
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }
        .status-badge {
            font-size: 0.7rem;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .status-pending { background-color: var(--accent-amber); color: #000; }
        .status-pass { background-color: var(--accent-green); color: #fff; }
        .status-revise { background-color: var(--accent-red); color: #fff; }
        /* 메시지 목록 */
        #messages-container {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .message-row {
            display: flex;
            gap: 14px;
            align-items: flex-start;
        }
        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            background-color: var(--bg-card);
            flex-shrink: 0;
        }
        .avatar-codex { background-color: #23a55a; color: #fff; }
        .avatar-agy { background-color: #5865f2; color: #fff; }
        .avatar-claude { background-color: #e67e22; color: #fff; }
        .avatar-user { background-color: #00a8fc; color: #fff; }
        .avatar-system { background-color: #636b75; color: #fff; }
        .message-content {
            flex: 1;
        }
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        .sender-name {
            font-weight: 600;
            font-size: 0.95rem;
        }
        .agent-tag {
            font-size: 0.65rem;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .tag-bot { background-color: var(--accent-primary); color: #fff; }
        .tag-human { background-color: #00a8fc; color: #fff; }
        .timestamp {
            font-size: 0.75rem;
            color: var(--text-muted);
        }
        .reply-quote {
            font-size: 0.8rem;
            color: var(--text-muted);
            border-left: 2px solid var(--border-color);
            padding-left: 8px;
            margin-bottom: 4px;
        }
        .message-body {
            font-size: 0.95rem;
            line-height: 1.45;
            white-space: pre-wrap;
            word-break: break-word;
        }
        /* 입력창 영역 */
        #input-area {
            padding: 16px 20px;
            background-color: var(--bg-chat);
            border-top: 1px solid var(--border-color);
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .sender-select {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-normal);
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 0.9rem;
            outline: none;
            cursor: pointer;
        }
        .input-box {
            flex: 1;
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-normal);
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
            transition: border 0.15s;
        }
        .input-box:focus {
            border-color: var(--accent-primary);
        }
        .send-btn {
            background-color: var(--accent-primary);
            color: #fff;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s;
        }
        .send-btn:hover {
            background-color: #4752c4;
        }
    </style>
</head>
<body>
    <!-- 좌측 사이드바 -->
    <div id="sidebar">
        <div class="sidebar-header">
            <span>🏛️ Agora Hub</span>
        </div>
        <div class="channel-list">
            <div class="channel-section-title">토론 채널 목록</div>
            <div id="channels-container">
                <!-- 동적 렌더링 -->
            </div>
        </div>
    </div>

    <!-- 중앙 채팅 본문 -->
    <div id="chat-area">
        <div class="chat-header">
            <div class="chat-title" id="current-channel-title">
                <span># general</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
                ● 실시간 연결 중 (1.5초 자동 동기화)
            </div>
        </div>

        <!-- 피어 리뷰 상태 배너 -->
        <div class="review-banner" id="review-banner" style="display: none;">
            <!-- 동적 리뷰 상태 카드 -->
        </div>

        <!-- 메시지 리스트 -->
        <div id="messages-container">
            <!-- 동적 메시지 -->
        </div>

        <!-- 입력창 -->
        <div id="input-area">
            <select id="sender-select" class="sender-select">
                <option value="user">👤 user (인간)</option>
                <option value="codex">🤖 codex (작업자)</option>
                <option value="agy">🛡️ agy (검토자)</option>
                <option value="claude">🟣 claude (에이전트)</option>
                <option value="conductor">🏛️ conductor (사회자)</option>
            </select>
            <input type="text" id="message-input" class="input-box" placeholder="메시지를 입력하세요 (Enter로 전송)..." autocomplete="off" />
            <button id="send-btn" class="send-btn">전송</button>
        </div>
    </div>

    <script>
        let currentChannel = 'general';
        let previousMessageCount = 0;

        const defaultChannels = ['general', 'review', 'task'];

        function getAvatarInfo(sender) {
            const s = (sender || '').toLowerCase();
            if (s.includes('codex')) return { icon: '🤖', cls: 'avatar-codex', tag: 'BOT' };
            if (s.includes('agy')) return { icon: '🛡️', cls: 'avatar-agy', tag: 'BOT' };
            if (s.includes('claude')) return { icon: '🟣', cls: 'avatar-claude', tag: 'BOT' };
            if (s.includes('user')) return { icon: '👤', cls: 'avatar-user', tag: 'HUMAN' };
            if (s.includes('conductor')) return { icon: '🏛️', cls: 'avatar-system', tag: 'HOST' };
            return { icon: '💬', cls: 'avatar-system', tag: 'AGENT' };
        }

        async function fetchChannels() {
            try {
                const res = await fetch('/api/channels');
                const data = await res.json();
                const container = document.getElementById('channels-container');

                // 기본 채널과 서버 반환 채널 병합
                const channelMap = {};
                defaultChannels.forEach(c => channelMap[c] = 0);
                data.forEach(c => channelMap[c.name] = c.message_count);

                let html = '';
                for (const [name, count] of Object.entries(channelMap)) {
                    const activeCls = name === currentChannel ? 'active' : '';
                    html += `
                        <div class="channel-item ${activeCls}" onclick="switchChannel('${name}')">
                            <span># ${name}</span>
                            <span class="channel-badge">${count}</span>
                        </div>
                    `;
                }
                container.innerHTML = html;
            } catch (err) {
                console.error('채널 목록 조회 오류:', err);
            }
        }

        async function fetchReviews() {
            const banner = document.getElementById('review-banner');
            if (currentChannel !== 'review') {
                banner.style.display = 'none';
                return;
            }
            try {
                const res = await fetch('/api/reviews');
                const reviews = await res.json();
                if (reviews.length === 0) {
                    banner.style.display = 'none';
                    return;
                }
                banner.style.display = 'flex';
                banner.innerHTML = reviews.map(r => {
                    let badgeCls = 'status-pending';
                    let text = 'PENDING';
                    if (r.verdict) {
                        text = r.verdict;
                        badgeCls = r.verdict === 'PASS' ? 'status-pass' : 'status-revise';
                    }
                    return `
                        <div class="review-card">
                            <span class="status-badge ${badgeCls}">${text}</span>
                            <strong>${r.requester} ➔ ${r.target_agent}</strong>
                            <span>${r.title}</span>
                        </div>
                    `;
                }).join('');
            } catch (err) {
                console.error('리뷰 현황 조회 오류:', err);
            }
        }

        async function fetchMessages() {
            try {
                const res = await fetch(`/api/messages?channel=${encodeURIComponent(currentChannel)}`);
                const messages = await res.json();
                const container = document.getElementById('messages-container');

                const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 50;

                let html = '';
                messages.forEach(msg => {
                    const avatar = getAvatarInfo(msg.sender);
                    const timeStr = new Date(msg.created_at).toLocaleTimeString('ko-KR', {
                        hour: '2-digit', minute: '2-digit', second: '2-digit'
                    });
                    const replyHtml = msg.reply_to ? `<div class="reply-quote">↳ Reply to ${msg.reply_to.slice(0, 8)}...</div>` : '';

                    html += `
                        <div class="message-row">
                            <div class="avatar ${avatar.cls}">${avatar.icon}</div>
                            <div class="message-content">
                                <div class="message-header">
                                    <span class="sender-name">${msg.sender}</span>
                                    <span class="agent-tag ${avatar.tag === 'HUMAN' ? 'tag-human' : 'tag-bot'}">${avatar.tag}</span>
                                    <span class="timestamp">${timeStr}</span>
                                </div>
                                ${replyHtml}
                                <div class="message-body">${escapeHtml(msg.content)}</div>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;

                // 새 메시지가 추가되었거나 스크롤이 하단에 있었으면 자동 스크롤
                if (messages.length !== previousMessageCount || isAtBottom) {
                    container.scrollTop = container.scrollHeight;
                    previousMessageCount = messages.length;
                }
            } catch (err) {
                console.error('메시지 조회 오류:', err);
            }
        }

        async function sendMessage() {
            const input = document.getElementById('message-input');
            const select = document.getElementById('sender-select');
            const content = input.value.trim();
            if (!content) return;

            const sender = select.value;
            input.value = '';

            try {
                await fetch('/api/messages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        sender: sender,
                        channel: currentChannel,
                        content: content
                    })
                });
                await fetchMessages();
                await fetchChannels();
            } catch (err) {
                alert('메시지 전송에 실패했습니다: ' + err);
            }
        }

        function switchChannel(name) {
            currentChannel = name;
            document.getElementById('current-channel-title').innerText = `# ${name}`;
            previousMessageCount = 0;
            fetchChannels();
            fetchMessages();
            fetchReviews();
        }

        function escapeHtml(text) {
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        document.getElementById('send-btn').addEventListener('click', sendMessage);
        document.getElementById('message-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // 초기 로드 및 1.5초 주기 동기화
        fetchChannels();
        fetchMessages();
        fetchReviews();
        setInterval(() => {
            fetchChannels();
            fetchMessages();
            fetchReviews();
        }, 1500);
    </script>
</body>
</html>
"""


async def handle_index(request: Request) -> HTMLResponse:
    """메인 HTML 채팅 대시보드 반환"""
    return HTMLResponse(HTML_TEMPLATE)


async def handle_get_channels(request: Request) -> JSONResponse:
    """활성 채널 목록 API"""
    channels = get_storage().list_channels()
    return JSONResponse([c.model_dump() for c in channels])


async def handle_get_messages(request: Request) -> JSONResponse:
    """채널별 메시지 조회 API"""
    channel = request.query_params.get("channel", "general")
    limit = int(request.query_params.get("limit", 50))
    messages = get_storage().read_messages(channel=channel, limit=limit)
    return JSONResponse([m.model_dump() for m in messages])


async def handle_post_message(request: Request) -> JSONResponse:
    """메시지 게시 API"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "잘못된 JSON 페이로드입니다."}, status_code=400)

    sender = body.get("sender", "user")
    channel = body.get("channel", "general")
    content = body.get("content", "")
    reply_to = body.get("reply_to")

    if not content:
        return JSONResponse({"error": "메시지 본문(content)이 비어있습니다."}, status_code=400)

    msg = get_storage().post_message(
        sender=sender,
        channel=channel,
        content=content,
        reply_to=reply_to,
    )
    return JSONResponse(msg.model_dump())


async def handle_get_reviews(request: Request) -> JSONResponse:
    """최근 피어 리뷰 목록 조회 API"""
    store = get_storage()
    # reviews 테이블에서 최근 10개 조회
    with store._lock:
        conn = store._get_connection()
        try:
            cursor = conn.execute("""
                SELECT id, requester, target_agent, title, content_diff_or_path,
                       status, verdict, comments, reviewer, created_at, updated_at
                FROM reviews
                ORDER BY created_at DESC
                LIMIT 10;
            """)
            rows = cursor.fetchall()
            reviews = [
                {
                    "id": r["id"],
                    "requester": r["requester"],
                    "target_agent": r["target_agent"],
                    "title": r["title"],
                    "status": r["status"],
                    "verdict": r["verdict"],
                    "comments": r["comments"],
                    "reviewer": r["reviewer"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
            return JSONResponse(reviews)
        finally:
            if store._in_memory_conn is None:
                conn.close()


def create_app(storage: Optional[AgoraStorage] = None) -> Starlette:
    """Starlette 웹 어플리케이션 팩토리"""
    if storage is not None:
        set_storage(storage)

    routes = [
        Route("/", handle_index, methods=["GET"]),
        Route("/api/channels", handle_get_channels, methods=["GET"]),
        Route("/api/messages", handle_get_messages, methods=["GET"]),
        Route("/api/messages", handle_post_message, methods=["POST"]),
        Route("/api/reviews", handle_get_reviews, methods=["GET"]),
    ]
    return Starlette(debug=True, routes=routes)


app = create_app()


def main():
    """웹 서버 실행 진입점"""
    import uvicorn
    get_storage().init_db()
    print("🏛️ Agora Web Chat 시작: http://localhost:8000")
    uvicorn.run("agora_mcp.web_chat:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
