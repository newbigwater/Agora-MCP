#!/usr/bin/env python3
"""
Agora Web Chat 실행 진입점 스크립트
브라우저에서 에이전트 간 실시간 대화와 피어 리뷰 현황을 관전하고 직접 메시지를 보낼 수 있습니다.
실행 방법: python run_web_chat.py
접속 주소: http://localhost:8000
"""
import sys
from pathlib import Path

# src 디렉터리를 모듈 탐색 경로에 추가
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from agora_mcp.web_chat import main

if __name__ == "__main__":
    main()
