"""
Pydantic 데이터 모델 단위 테스트
"""
import pytest
from pydantic import ValidationError
from agora_mcp.models import (
    Message,
    Review,
    ReviewVerdict,
    ReviewStatus,
    ChannelSummary,
)


def test_message_creation_defaults():
    """기본 필드 자동 생성을 포함한 메시지 생성 검증"""
    msg = Message(sender="claude", channel="general", content="안녕하세요 아고라!")
    assert msg.sender == "claude"
    assert msg.channel == "general"
    assert msg.content == "안녕하세요 아고라!"
    assert msg.reply_to is None
    assert msg.id is not None
    assert len(msg.id) > 0
    assert msg.created_at is not None


def test_message_with_reply():
    """답글(reply_to)이 지정된 메시지 생성 검증"""
    msg = Message(
        sender="agy",
        channel="review",
        content="확인했습니다.",
        reply_to="msg-1234",
    )
    assert msg.reply_to == "msg-1234"


def test_review_verdict_values():
    """리뷰 결과 열거형 값 검증"""
    assert ReviewVerdict.PASS == "PASS"
    assert ReviewVerdict.REVISE == "REVISE"
    assert ReviewVerdict.FAIL == "FAIL"


def test_review_creation_defaults():
    """기본 상태(PENDING)를 가진 리뷰 요청 생성 검증"""
    review = Review(
        requester="claude",
        target_agent="codex",
        title="인증 모듈 리팩토링 검토",
        content_diff_or_path="src/auth.py diff ...",
    )
    assert review.status == ReviewStatus.PENDING
    assert review.verdict is None
    assert review.reviewer is None
    assert review.comments is None
    assert review.id is not None
    assert review.created_at is not None
    assert review.updated_at is not None


def test_review_verdict_validation():
    """리뷰 결과 유효성 검사 및 정규화 검증"""
    review = Review(
        requester="claude",
        target_agent="agy",
        title="테스트 검토",
        content_diff_or_path="diff",
        status=ReviewStatus.COMPLETED,
        verdict=ReviewVerdict.PASS,
        reviewer="agy",
        comments="LGTM! 통과합니다.",
    )
    assert review.verdict == ReviewVerdict.PASS
    assert review.status == ReviewStatus.COMPLETED

    # 유효하지 않은 평결(Verdict) 입력 시 검증 실패 확인
    with pytest.raises(ValidationError):
        Review(
            requester="claude",
            target_agent="agy",
            title="테스트",
            content_diff_or_path="diff",
            verdict="INVALID_VERDICT",  # type: ignore
        )


def test_channel_summary():
    """채널 요약 모델 검증"""
    summary = ChannelSummary(
        name="general",
        message_count=5,
        last_activity="2026-10-22T12:00:00Z",
    )
    assert summary.name == "general"
    assert summary.message_count == 5
