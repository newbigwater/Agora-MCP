"""
SQLite 스토리지 계층 단위 테스트
"""
import pytest
from agora_mcp.storage import AgoraStorage
from agora_mcp.models import ReviewStatus, ReviewVerdict


@pytest.fixture
def storage():
    """테스트용 인메모리 스토리지 인스턴스 픽스처"""
    store = AgoraStorage(db_path=":memory:")
    store.init_db()
    return store


def test_post_and_read_messages(storage):
    """메시지 게시 및 채널별 조회 검증"""
    msg1 = storage.post_message(sender="claude", channel="general", content="첫 번째 메시지")
    msg2 = storage.post_message(sender="codex", channel="general", content="두 번째 메시지", reply_to=msg1.id)

    # general 채널 메시지 조회
    messages = storage.read_messages(channel="general", limit=10)
    assert len(messages) == 2
    assert messages[0].id == msg1.id
    assert messages[1].id == msg2.id
    assert messages[1].reply_to == msg1.id

    # 비어있는 채널 조회 시 빈 리스트 반환
    empty_messages = storage.read_messages(channel="nonexistent", limit=10)
    assert empty_messages == []


def test_read_messages_limit(storage):
    """메시지 조회 개수 제한(limit) 검증"""
    for i in range(15):
        storage.post_message(sender="agy", channel="task", content=f"작업 {i}")

    messages = storage.read_messages(channel="task", limit=5)
    assert len(messages) == 5
    # 최신 메시지 5개가 올바른 시간 순서로 정렬되는지 확인
    assert messages[-1].content == "작업 14"


def test_unread_messages_tracking(storage):
    """에이전트별 읽음 처리 및 미독 메시지 격리 검증"""
    msg1 = storage.post_message(sender="claude", channel="review", content="검토 요청 1")
    msg2 = storage.post_message(sender="claude", channel="review", content="검토 요청 2")

    # codex 에이전트가 미독 메시지 조회 -> 2개 반환 및 읽음 처리됨
    codex_unread = storage.read_messages(channel="review", unread_only=True, agent_id="codex")
    assert len(codex_unread) == 2

    # codex 에이전트가 다시 미독 메시지 조회 -> 이미 읽었으므로 0개
    codex_unread_again = storage.read_messages(channel="review", unread_only=True, agent_id="codex")
    assert len(codex_unread_again) == 0

    # agy 에이전트는 아직 읽지 않았으므로 2개가 조회되어야 함
    agy_unread = storage.read_messages(channel="review", unread_only=True, agent_id="agy")
    assert len(agy_unread) == 2


def test_list_channels(storage):
    """활성 채널 목록 및 메시지 집계 검증"""
    storage.post_message(sender="claude", channel="general", content="안녕")
    storage.post_message(sender="agy", channel="general", content="반가워")
    storage.post_message(sender="codex", channel="task", content="작업 시작")

    channels = storage.list_channels()
    channel_map = {ch.name: ch for ch in channels}

    assert "general" in channel_map
    assert "task" in channel_map
    assert channel_map["general"].message_count == 2
    assert channel_map["task"].message_count == 1
    assert channel_map["general"].last_activity is not None


def test_review_lifecycle(storage):
    """코드 검토 요청, 상태 조회 및 평결 제출 라이프사이클 검증"""
    review = storage.create_review(
        requester="claude",
        target_agent="codex",
        title="DB 마이그레이션 검토",
        content_diff_or_path="migrations/001_init.sql",
    )
    assert review.status == ReviewStatus.PENDING
    assert review.requester == "claude"
    assert review.target_agent == "codex"

    # 리뷰 단건 조회
    fetched = storage.get_review(review.id)
    assert fetched is not None
    assert fetched.id == review.id
    assert fetched.status == ReviewStatus.PENDING

    # 리뷰 결과 제출 (PASS)
    updated = storage.submit_review(
        review_id=review.id,
        reviewer="codex",
        verdict=ReviewVerdict.PASS,
        comments="인덱스와 롤백 구문 모두 적절합니다. 승인합니다.",
    )
    assert updated.status == ReviewStatus.COMPLETED
    assert updated.verdict == ReviewVerdict.PASS
    assert updated.reviewer == "codex"
    assert updated.comments == "인덱스와 롤백 구문 모두 적절합니다. 승인합니다."

    # 다시 조회하여 영속성 확인
    final_review = storage.get_review(review.id)
    assert final_review.status == ReviewStatus.COMPLETED
    assert final_review.verdict == ReviewVerdict.PASS


def test_submit_review_not_found(storage):
    """존재하지 않는 review_id로 제출 시 KeyError 발생 검증"""
    with pytest.raises(KeyError):
        storage.submit_review(
            review_id="non-existent-uuid",
            reviewer="codex",
            verdict=ReviewVerdict.FAIL,
            comments="존재하지 않는 리뷰입니다.",
        )
