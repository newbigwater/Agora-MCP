"""
Agora-MCP FastMCP 서버 정의
AI 코딩 에이전트 간 메시징 및 피어 리뷰 MCP Tool을 노출합니다.
"""
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from agora_mcp.models import ReviewVerdict
from agora_mcp.storage import AgoraStorage

# FastMCP 인스턴스 생성
mcp = FastMCP("agora")

# 전역 스토리지 인스턴스 (lazy initialize)
_storage: Optional[AgoraStorage] = None


def get_storage() -> AgoraStorage:
    """현재 설정된 AgoraStorage 인스턴스 반환 (없을 시 기본값으로 초기화)"""
    global _storage
    if _storage is None:
        _storage = AgoraStorage()
        _storage.init_db()
    return _storage


def set_storage(storage: AgoraStorage) -> None:
    """테스트 또는 사용자 정의 스토리지를 설정"""
    global _storage
    _storage = storage


@mcp.tool()
def post_message(
    sender: str,
    channel: str,
    content: str,
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    특정 채널에 메시지를 게시합니다.

    Args:
        sender: 발신 에이전트 식별자 (예: claude, agy, codex)
        channel: 대상 채널명 (예: general, review, task)
        content: 메시지 본문
        reply_to: (선택 사항) 회신할 대상 메시지 ID

    Returns:
        생성된 메시지 정보 딕셔너리
    """
    msg = get_storage().post_message(
        sender=sender,
        channel=channel,
        content=content,
        reply_to=reply_to,
    )
    return msg.model_dump()


@mcp.tool()
def read_messages(
    channel: str,
    limit: int = 10,
    unread_only: bool = False,
    agent_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    특정 채널의 메시지 목록을 조회합니다.

    Args:
        channel: 조회할 채널명
        limit: 조회할 최대 메시지 수 (기본값: 10)
        unread_only: 미독 메시지만 조회할지 여부 (기본값: False)
        agent_id: (선택 사항) 조회를 요청하는 에이전트 식별자 (지정 시 읽음 처리 반영)

    Returns:
        메시지 객체 딕셔너리 목록 (시간순 정렬)
    """
    messages = get_storage().read_messages(
        channel=channel,
        limit=limit,
        unread_only=unread_only,
        agent_id=agent_id,
    )
    return [m.model_dump() for m in messages]


@mcp.tool()
def list_channels() -> List[Dict[str, Any]]:
    """
    활성화된 모든 채널과 채널별 메시지 수, 마지막 활동 시각을 반환합니다.

    Returns:
        활성 채널 현황 요약 목록
    """
    channels = get_storage().list_channels()
    return [c.model_dump() for c in channels]


@mcp.tool()
def request_review(
    requester: str,
    target_agent: str,
    title: str,
    content_diff_or_path: str,
) -> Dict[str, Any]:
    """
    특정 대상 에이전트에게 코드 검토(Peer Review)를 요청합니다.
    요청 발행 시 review 채널에 자동으로 알림 메시지가 게시됩니다.

    Args:
        requester: 검토를 요청하는 에이전트 식별자
        target_agent: 검토를 위임할 대상 에이전트 식별자
        title: 검토 요청 요약 제목
        content_diff_or_path: 검토할 git diff 또는 파일 경로

    Returns:
        생성된 리뷰 요청 세부 정보
    """
    store = get_storage()
    review = store.create_review(
        requester=requester,
        target_agent=target_agent,
        title=title,
        content_diff_or_path=content_diff_or_path,
    )

    # review 채널에 자동 알림 게시
    notice = (
        f"🔔 [코드 검토 요청] {requester} -> {target_agent}\n"
        f"제목: {title}\n"
        f"리뷰 ID: {review.id}"
    )
    store.post_message(sender=requester, channel="review", content=notice)

    return review.model_dump()


@mcp.tool()
def submit_review(
    review_id: str,
    reviewer: str,
    verdict: str,
    comments: str,
) -> Dict[str, Any]:
    """
    진행 중인 코드 검토에 대해 평결(Verdict) 및 상세 피드백을 제출합니다.
    제출 시 review 채널에 검토 결과 알림이 게시됩니다.

    Args:
        review_id: 대상 리뷰 고유 ID
        reviewer: 검토를 수행한 에이전트 식별자
        verdict: 검토 결과 평결 (PASS, REVISE, FAIL 중 하나, 대소문자 무관)
        comments: 상세 검토 코멘트 및 개선 제안

    Returns:
        업데이트 완료된 리뷰 정보
    """
    # 평결 유효성 검사 및 정규화
    try:
        verdict_enum = ReviewVerdict(verdict.strip().upper())
    except (ValueError, AttributeError):
        raise ValueError(
            f"유효하지 않은 평결입니다: '{verdict}'. PASS, REVISE, FAIL 중 하나여야 합니다."
        )

    store = get_storage()
    updated_review = store.submit_review(
        review_id=review_id,
        reviewer=reviewer,
        verdict=verdict_enum,
        comments=comments,
    )

    # review 채널에 결과 알림 게시
    notice = (
        f"📝 [코드 검토 완료] {reviewer} ({verdict_enum.value})\n"
        f"리뷰 ID: {review_id}\n"
        f"의견: {comments}"
    )
    store.post_message(sender=reviewer, channel="review", content=notice)

    return updated_review.model_dump()


@mcp.tool()
def get_review_status(review_id: str) -> Dict[str, Any]:
    """
    특정 리뷰의 현재 진행 상태(PENDING/COMPLETED) 및 평결 결과를 조회합니다.

    Args:
        review_id: 조회할 리뷰 ID

    Returns:
        해당 리뷰의 전체 상태 정보
    """
    review = get_storage().get_review(review_id)
    if review is None:
        raise ValueError(f"리뷰 ID '{review_id}'에 해당하는 검토 건을 찾을 수 없습니다.")
    return review.model_dump()


def main():
    """서버 진입점 실행 (FastMCP stdio 트랜스포트 기본 구동)"""
    # 기동 시 DB 초기화 보장
    get_storage().init_db()
    mcp.run()


if __name__ == "__main__":
    main()
