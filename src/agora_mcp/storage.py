"""
SQLite 데이터 영속성 계층
에이전트 간 메시지, 채널 히스토리, 피어 리뷰 상태를 로컬 SQLite에 안전하게 영속화합니다.
"""
import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional, List
from agora_mcp.models import (
    Message,
    Review,
    ReviewStatus,
    ReviewVerdict,
    ChannelSummary,
    get_current_utc_iso,
)


class AgoraStorage:
    """로컬 SQLite 기반 Agora 영속성 스토리지 관리자"""

    def __init__(self, db_path: Optional[str | Path] = None):
        """스토리지 초기화 및 DB 경로 설정"""
        if db_path is None:
            env_path = os.environ.get("AGORA_DB_PATH")
            if env_path:
                self.db_path = str(env_path)
            else:
                default_dir = Path.home() / ".agora"
                default_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = str(default_dir / "agora.db")
        else:
            self.db_path = str(db_path)

        self._lock = threading.Lock()
        self._in_memory_conn: Optional[sqlite3.Connection] = None

        if self.db_path == ":memory:":
            # 인메모리 DB는 연결이 닫히면 휘발되므로 단일 커넥션을 유지
            self._in_memory_conn = sqlite3.connect(
                ":memory:", check_same_thread=False
            )
            self._in_memory_conn.row_factory = sqlite3.Row
        else:
            parent = Path(self.db_path).parent
            parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """스레드 안전한 데이터베이스 커넥션 반환"""
        if self._in_memory_conn is not None:
            return self._in_memory_conn

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL 모드 활성화로 다중 에이전트 동시 접근 성능 보장
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """데이터베이스 테이블 및 인덱스 초기화"""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    # 1. 메시지 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS messages (
                            id TEXT PRIMARY KEY,
                            sender TEXT NOT NULL,
                            channel TEXT NOT NULL,
                            content TEXT NOT NULL,
                            reply_to TEXT,
                            created_at TEXT NOT NULL
                        );
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_messages_channel_created
                        ON messages (channel, created_at);
                    """)

                    # 2. 에이전트별 메시지 읽음 상태 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS message_reads (
                            message_id TEXT NOT NULL,
                            agent_id TEXT NOT NULL,
                            read_at TEXT NOT NULL,
                            PRIMARY KEY (message_id, agent_id),
                            FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
                        );
                    """)

                    # 3. 피어 리뷰 워크플로우 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS reviews (
                            id TEXT PRIMARY KEY,
                            requester TEXT NOT NULL,
                            target_agent TEXT NOT NULL,
                            title TEXT NOT NULL,
                            content_diff_or_path TEXT NOT NULL,
                            status TEXT NOT NULL,
                            verdict TEXT,
                            comments TEXT,
                            reviewer TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        );
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_reviews_status
                        ON reviews (status);
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_reviews_target
                        ON reviews (target_agent);
                    """)
            finally:
                if self._in_memory_conn is None:
                    conn.close()

    def post_message(
        self,
        sender: str,
        channel: str,
        content: str,
        reply_to: Optional[str] = None,
    ) -> Message:
        """새 메시지를 채널에 게시하고 저장"""
        msg = Message(
            sender=sender,
            channel=channel,
            content=content,
            reply_to=reply_to,
        )
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO messages (id, sender, channel, content, reply_to, created_at)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (msg.id, msg.sender, msg.channel, msg.content, msg.reply_to, msg.created_at),
                    )
            finally:
                if self._in_memory_conn is None:
                    conn.close()
        return msg

    def read_messages(
        self,
        channel: str,
        limit: int = 10,
        unread_only: bool = False,
        agent_id: Optional[str] = None,
    ) -> List[Message]:
        """채널 내 메시지를 조회하고 에이전트 지정 시 읽음 처리 수행"""
        with self._lock:
            conn = self._get_connection()
            try:
                if unread_only and agent_id:
                    cursor = conn.execute(
                        """
                        SELECT id, sender, channel, content, reply_to, created_at
                        FROM messages
                        WHERE channel = ?
                          AND id NOT IN (
                              SELECT message_id FROM message_reads WHERE agent_id = ?
                          )
                        ORDER BY created_at DESC
                        LIMIT ?;
                        """,
                        (channel, agent_id, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT id, sender, channel, content, reply_to, created_at
                        FROM messages
                        WHERE channel = ?
                        ORDER BY created_at DESC
                        LIMIT ?;
                        """,
                        (channel, limit),
                    )
                rows = cursor.fetchall()
                # 과거 순서(오름차순)로 정렬하여 반환
                messages = [
                    Message(
                        id=row["id"],
                        sender=row["sender"],
                        channel=row["channel"],
                        content=row["content"],
                        reply_to=row["reply_to"],
                        created_at=row["created_at"],
                    )
                    for row in reversed(rows)
                ]

                # 조회한 메시지를 해당 에이전트의 읽음 상태로 기록
                if agent_id and messages:
                    now = get_current_utc_iso()
                    with conn:
                        for m in messages:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO message_reads (message_id, agent_id, read_at)
                                VALUES (?, ?, ?);
                                """,
                                (m.id, agent_id, now),
                            )
                return messages
            finally:
                if self._in_memory_conn is None:
                    conn.close()

    def list_channels(self) -> List[ChannelSummary]:
        """등록된 모든 활성 채널 목록 및 메시지 통계 반환"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT channel, COUNT(*) as cnt, MAX(created_at) as last_act
                    FROM messages
                    GROUP BY channel
                    ORDER BY MAX(created_at) DESC;
                    """
                )
                rows = cursor.fetchall()
                return [
                    ChannelSummary(
                        name=row["channel"],
                        message_count=row["cnt"],
                        last_activity=row["last_act"],
                    )
                    for row in rows
                ]
            finally:
                if self._in_memory_conn is None:
                    conn.close()

    def create_review(
        self,
        requester: str,
        target_agent: str,
        title: str,
        content_diff_or_path: str,
    ) -> Review:
        """신규 피어 리뷰 요청 생성 및 저장"""
        review = Review(
            requester=requester,
            target_agent=target_agent,
            title=title,
            content_diff_or_path=content_diff_or_path,
            status=ReviewStatus.PENDING,
        )
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO reviews (
                            id, requester, target_agent, title, content_diff_or_path,
                            status, verdict, comments, reviewer, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            review.id,
                            review.requester,
                            review.target_agent,
                            review.title,
                            review.content_diff_or_path,
                            review.status.value,
                            review.verdict.value if review.verdict else None,
                            review.comments,
                            review.reviewer,
                            review.created_at,
                            review.updated_at,
                        ),
                    )
            finally:
                if self._in_memory_conn is None:
                    conn.close()
        return review

    def get_review(self, review_id: str) -> Optional[Review]:
        """특정 리뷰 ID의 상세 현황 조회"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT id, requester, target_agent, title, content_diff_or_path,
                           status, verdict, comments, reviewer, created_at, updated_at
                    FROM reviews
                    WHERE id = ?;
                    """,
                    (review_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return Review(
                    id=row["id"],
                    requester=row["requester"],
                    target_agent=row["target_agent"],
                    title=row["title"],
                    content_diff_or_path=row["content_diff_or_path"],
                    status=ReviewStatus(row["status"]),
                    verdict=ReviewVerdict(row["verdict"]) if row["verdict"] else None,
                    comments=row["comments"],
                    reviewer=row["reviewer"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            finally:
                if self._in_memory_conn is None:
                    conn.close()

    def submit_review(
        self,
        review_id: str,
        reviewer: str,
        verdict: ReviewVerdict | str,
        comments: str,
    ) -> Review:
        """리뷰 검토 결과 및 피드백 제출"""
        # 평결 검증 및 정규화
        if isinstance(verdict, str):
            verdict = ReviewVerdict(verdict.strip().upper())

        updated_at = get_current_utc_iso()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE reviews
                        SET status = ?, verdict = ?, comments = ?, reviewer = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (
                            ReviewStatus.COMPLETED.value,
                            verdict.value,
                            comments,
                            reviewer,
                            updated_at,
                            review_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        raise KeyError(f"리뷰 ID를 찾을 수 없습니다: {review_id}")
            finally:
                if self._in_memory_conn is None:
                    conn.close()

        fetched = self.get_review(review_id)
        if fetched is None:
            raise KeyError(f"업데이트 후 리뷰 조회 실패: {review_id}")
        return fetched
