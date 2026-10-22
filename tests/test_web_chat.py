"""
Agora Web Chat UI 단위 및 통합 테스트
"""
import pytest
from starlette.testclient import TestClient
from agora_mcp.storage import AgoraStorage
from agora_mcp.web_chat import create_app, set_storage


@pytest.fixture
def chat_client():
    """인메모리 스토리지와 연동된 테스트용 웹 클라이언트 생성"""
    store = AgoraStorage(db_path=":memory:")
    store.init_db()
    set_storage(store)
    app = create_app(store)
    return TestClient(app)


def test_index_page(chat_client):
    """메인 웹 채팅 페이지 렌더링 확인"""
    res = chat_client.get("/")
    assert res.status_code == 200
    assert "Agora Chat Hub" in res.text


def test_api_channels(chat_client):
    """채널 목록 API 검증"""
    res = chat_client.get("/api/channels")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_post_and_get_messages(chat_client):
    """메시지 전송 및 조회 API 검증"""
    # 1. 메시지 작성
    post_res = chat_client.post(
        "/api/messages",
        json={
            "sender": "user",
            "channel": "general",
            "content": "웹 채팅 테스트 메시지입니다.",
        },
    )
    assert post_res.status_code == 200
    msg_data = post_res.json()
    assert msg_data["sender"] == "user"
    assert msg_data["content"] == "웹 채팅 테스트 메시지입니다."

    # 2. 채널 메시지 조회
    get_res = chat_client.get("/api/messages?channel=general")
    assert get_res.status_code == 200
    messages = get_res.json()
    assert len(messages) >= 1
    assert any(m["content"] == "웹 채팅 테스트 메시지입니다." for m in messages)


def test_api_reviews(chat_client):
    """피어 리뷰 목록 API 검증"""
    res = chat_client.get("/api/reviews")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
