#!/usr/bin/env python3
"""
Agora-MCP 서버 실행 진입점 스크립트
명령줄 또는 MCP 클라이언트에서 직접 실행할 수 있습니다.
예: python run_server.py
"""
import sys
from pathlib import Path

# src 경로를 모듈 탐색 경로에 추가
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from agora_mcp.server import main

if __name__ == "__main__":
    main()
