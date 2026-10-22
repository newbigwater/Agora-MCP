"""
Agora-MCP 로컬 기능 스모크 테스트 스크립트
FastMCP 서버 도구들을 직접 호출하여 메시지 교환 및 피어 리뷰 전체 시나리오를 시뮬레이션합니다.
실행 방법: python scripts/smoke_test.py
"""
import sys
from pathlib import Path

# src 디렉터리를 모듈 탐색 경로에 추가
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from agora_mcp.server import (
    post_message,
    read_messages,
    list_channels,
    request_review,
    submit_review,
    get_review_status,
)


def run_smoke_test():
    print("=" * 60)
    print("🏛️  Agora-MCP 스모크 테스트 시작")
    print("=" * 60)

    # 1. 메시지 게시 테스트
    print("\n[1] 메시지 게시 (post_message)...")
    msg1 = post_message(
        sender="claude",
        channel="general",
        content="안녕하세요 아고라 광장! 새로운 태스크 협업을 시작합니다.",
    )
    print(f"  -> 게시 완료 (ID: {msg1['id']}, 채널: {msg1['channel']})")

    # 2. 답글 게시 테스트
    print("\n[2] 답글 게시 (post_message with reply_to)...")
    msg2 = post_message(
        sender="codex",
        channel="general",
        content="반갑습니다 claude! 인증 모듈 구현 태스크를 맡겠습니다.",
        reply_to=msg1["id"],
    )
    print(f"  -> 답글 게시 완료 (ID: {msg2['id']}, 원본 ID: {msg2['reply_to']})")

    # 3. 채널 목록 조회
    print("\n[3] 채널 목록 조회 (list_channels)...")
    channels = list_channels()
    for ch in channels:
        print(f"  - 채널: #{ch['name']} (메시지 수: {ch['message_count']}, 최근 활동: {ch['last_activity']})")

    # 4. 채널 메시지 읽기
    print("\n[4] general 채널 메시지 읽기 (read_messages)...")
    messages = read_messages(channel="general", limit=5)
    for m in messages:
        print(f"  [{m['sender']}] {m['content']}")

    # 5. 피어 리뷰 요청 발행
    print("\n[5] 피어 리뷰 요청 발행 (request_review)...")
    review_req = request_review(
        requester="codex",
        target_agent="agy",
        title="JWT 인증 토큰 만료 로직 개선안",
        content_diff_or_path="diff --git a/jwt.py b/jwt.py\n+ def verify_exp(token): return True",
    )
    review_id = review_req["id"]
    print(f"  -> 리뷰 요청 생성 완료 (ID: {review_id}, 상태: {review_req['status']})")

    # 6. 리뷰 채널 알림 확인
    print("\n[6] review 채널 알림 메시지 확인 (read_messages)...")
    review_msgs = read_messages(channel="review", limit=2)
    for rm in review_msgs:
        print(f"  📢 {rm['content']}")

    # 7. 피어 리뷰 제출 (PASS)
    print("\n[7] 피어 리뷰 결과 제출 (submit_review)...")
    completed = submit_review(
        review_id=review_id,
        reviewer="agy",
        verdict="PASS",
        comments="토큰 검증 로직이 안전하게 구현되었습니다. 승인합니다.",
    )
    print(f"  -> 리뷰 결과: {completed['verdict']} (검토자: {completed['reviewer']})")

    # 8. 최종 리뷰 상태 조회
    print("\n[8] 최종 리뷰 상태 조회 (get_review_status)...")
    status = get_review_status(review_id=review_id)
    print(f"  -> ID: {status['id']}")
    print(f"  -> 상태: {status['status']}")
    print(f"  -> 평결: {status['verdict']}")
    print(f"  -> 코멘트: {status['comments']}")

    print("\n" + "=" * 60)
    print("✅ 모든 Agora-MCP 기능 스모크 테스트 성공!")
    print("=" * 60)


if __name__ == "__main__":
    run_smoke_test()
