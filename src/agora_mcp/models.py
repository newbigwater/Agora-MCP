"""
Agora-MCP 데이터 모델 정의
Pydantic v2 기반의 메시지, 코드 리뷰, 채널 상태 데이터 구조
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ReviewVerdict(str, Enum):
    """코드 검토 결과 평결 열거형"""
    PASS = "PASS"
    REVISE = "REVISE"
    FAIL = "FAIL"


class ReviewStatus(str, Enum):
    """리뷰 요청의 진행 상태"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


def get_current_utc_iso() -> str:
    """현재 UTC 시각을 ISO 8601 문자열로 반환"""
    return datetime.now(timezone.utc).isoformat()


class Message(BaseModel):
    """에이전트 간 비동기 메시지 모델"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = Field(description="메시지 발신자 에이전트 식별자 (예: claude, agy, codex)")
    channel: str = Field(description="대상 채널명 (예: general, review, task)")
    content: str = Field(description="메시지 본문 내용")
    reply_to: Optional[str] = Field(default=None, description="회신 대상 메시지 ID")
    created_at: str = Field(default_factory=get_current_utc_iso, description="메시지 생성 시각 (ISO 8601)")


class Review(BaseModel):
    """에이전트 간 피어 리뷰 요청 및 결과 모델"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    requester: str = Field(description="검토를 요청한 에이전트 식별자")
    target_agent: str = Field(description="검토를 요청받은 대상 에이전트 식별자")
    title: str = Field(description="검토 요청 제목")
    content_diff_or_path: str = Field(description="검토할 코드 diff 본문 또는 파일 경로")
    status: ReviewStatus = Field(default=ReviewStatus.PENDING, description="리뷰 진행 상태")
    verdict: Optional[ReviewVerdict] = Field(default=None, description="검토 평결 (PASS, REVISE, FAIL)")
    comments: Optional[str] = Field(default=None, description="검토자의 상세 피드백 코멘트")
    reviewer: Optional[str] = Field(default=None, description="실제 검토를 수행한 에이전트")
    created_at: str = Field(default_factory=get_current_utc_iso, description="요청 생성 시각")
    updated_at: str = Field(default_factory=get_current_utc_iso, description="상태 변경 시각")

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, value):
        """대소문자 무관하게 평결을 ReviewVerdict 열거형으로 변환"""
        if value is None:
            return None
        if isinstance(value, ReviewVerdict):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            try:
                return ReviewVerdict(normalized)
            except ValueError:
                raise ValueError(f"유효하지 않은 검토 결과입니다: {value}. PASS, REVISE, FAIL 중 하나여야 합니다.")
        raise ValueError(f"올바르지 않은 평결 타입: {type(value)}")


class ChannelSummary(BaseModel):
    """활성 채널 현황 요약 모델"""
    name: str = Field(description="채널 이름")
    message_count: int = Field(default=0, description="채널 내 총 메시지 수")
    last_activity: Optional[str] = Field(default=None, description="마지막 메시지 게시 시각")
