"""
FastMCP 서버 및 Tool 동작 단위/통합 테스트
"""
import pytest
from agora_mcp.server import (
    mcp,
    set_storage,
    post_message,
    read_messages,
    list_channels,
    request_review,
    submit_review,
    get_review_status,
)
from agora_mcp.storage import AgoraStorage


@pytest.fixture(autouse=True)
def isolated_storage():
    """각 테스트마다 독립된 인메모리 스토리지 주입"""
    test_storage = AgoraStorage(db_path=":memory:")
    test_storage.init_db()
    set_storage(test_storage)
    return test_storage


def test_mcp_instance_registered():
    """FastMCP 인스턴스 이름 및 Tool 등록 확인"""
    assert mcp.name == "agora"
    # mcp 객체에 도구들이 정상 등록되었는지 확인
    # FastMCP는 _tool_manager.list_tools() 또는 list_tools() 지원
    tool_names = [tool.name for tool in mcp._tool_manager.list_tools()]
    expected_tools = {
        "post_message",
        "read_messages",
        "list_channels",
        "request_review",
        "submit_review",
        "get_review_status",
    }
    assert expected_tools.issubset(set(tool_names))


def test_messaging_workflow():
    """메시징 도구(post_message, read_messages, list_channels) 동작 검증"""
    # 1. 메시지 작성
    msg1 = post_message(sender="claude", channel="general", content="안녕하세요 아고라!")
    assert msg1["sender"] == "claude"
    assert msg1["channel"] == "general"
    assert msg1["content"] == "안녕하세요 아고라!"
    assert "id" in msg1

    # 2. 답글 작성
    msg2 = post_message(sender="agy", channel="general", content="반갑습니다 claude!", reply_to=msg1["id"])
    assert msg2["reply_to"] == msg1["id"]

    # 3. 채널 메시지 읽기
    messages = read_messages(channel="general", limit=10)
    assert len(messages) == 2
    assert messages[0]["id"] == msg1["id"]
    assert messages[1]["id"] == msg2["id"]

    # 4. 채널 목록 조회
    channels = list_channels()
    assert any(c["name"] == "general" and c["message_count"] == 2 for c in channels)


def test_unread_messages_flow():
    """미독 메시지 필터링 및 에이전트별 읽음 처리 도구 검증"""
    post_message(sender="system", channel="alerts", content="경보 1")
    post_message(sender="system", channel="alerts", content="경보 2")

    # codex가 alerts 채널의 미독 메시지 조회
    unread_codex = read_messages(channel="alerts", limit=10, unread_only=True, agent_id="codex")
    assert len(unread_codex) == 2

    # 다시 조회 시 미독 메시지 없음
    unread_codex_again = read_messages(channel="alerts", limit=10, unread_only=True, agent_id="codex")
    assert len(unread_codex_again) == 0

    # claude는 아직 읽지 않았으므로 2건 조회
    unread_claude = read_messages(channel="alerts", limit=10, unread_only=True, agent_id="claude")
    assert len(unread_claude) == 2


def test_peer_review_workflow():
    """피어 리뷰 워크플로우(request_review, submit_review, get_review_status) 통합 검증"""
    # 1. 리뷰 요청 발행
    review_req = request_review(
        requester="claude",
        target_agent="codex",
        title="신규 인증 모듈 보안 검토",
        content_diff_or_path="diff --git a/auth.py b/auth.py...",
    )
    assert review_req["requester"] == "claude"
    assert review_req["target_agent"] == "codex"
    assert review_req["status"] == "PENDING"
    review_id = review_req["id"]

    # 리뷰 채널에 알림 메시지가 자동 등록되었는지 확인
    review_channel_msgs = read_messages(channel="review", limit=5)
    assert len(review_channel_msgs) >= 1
    assert review_id in review_channel_msgs[0]["content"]

    # 2. 리뷰 현황 단건 조회
    status = get_review_status(review_id=review_id)
    assert status["id"] == review_id
    assert status["status"] == "PENDING"
    assert status["verdict"] is None

    # 3. 리뷰 결과 제출 (REVISE)
    completed_review = submit_review(
        review_id=review_id,
        reviewer="codex",
        verdict="REVISE",
        comments="토큰 만료 시간 검증 로직 추가 필요합니다.",
    )
    assert completed_review["id"] == review_id
    assert completed_review["status"] == "COMPLETED"
    assert completed_review["verdict"] == "REVISE"
    assert completed_review["reviewer"] == "codex"

    # 4. 재조회하여 최종 상태 반영 확인
    final_status = get_review_status(review_id=review_id)
    assert final_status["status"] == "COMPLETED"
    assert final_status["verdict"] == "REVISE"


def test_submit_review_invalid_verdict():
    """유효하지 않은 평결 입력 시 ValueError 발생 검증"""
    review_req = request_review(
        requester="claude",
        target_agent="agy",
        title="SQL 쿼리 검토",
        content_diff_or_path="SELECT * FROM users",
    )
    with pytest.raises(ValueError):
        submit_review(
            review_id=review_req["id"],
            reviewer="agy",
            verdict="NOT_VALID",
            comments="잘못된 평결",
        )


def test_get_review_status_not_found():
    """존재하지 않는 review_id 조회 시 ValueError 또는 KeyError 검증"""
    with pytest.raises((KeyError, ValueError)):
        get_review_status(review_id="unknown-uuid")
