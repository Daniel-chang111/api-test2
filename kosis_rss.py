"""KOSIS 공지사항 RSS를 읽어 JSON 또는 콘솔 목록으로 출력한다.

사용 예시:
    python3 kosis_rss.py
    python3 kosis_rss.py --limit 5 --json
    python3 kosis_rss.py --output kosis_notices.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


# KOSIS RSS 안내 페이지에서 제공하는 공지사항 공식 피드 주소
RSS_URL = "https://kosis.kr/rss/notice_rss.jsp"
TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_text(value: str | None) -> str:
    """RSS 설명에 들어 있는 HTML 태그와 불필요한 공백을 제거한다."""
    without_tags = TAG_PATTERN.sub(" ", value or "")
    return WHITESPACE_PATTERN.sub(" ", html.unescape(without_tags)).strip()


def read_notices(url: str = RSS_URL, timeout: int = 15) -> list[dict[str, str]]:
    """RSS를 내려받아 공지 목록으로 변환한다."""
    request = Request(
        url,
        headers={
            "Accept": "application/rss+xml, application/xml, text/xml",
            "User-Agent": "KOSIS-RSS-Reader/1.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            xml_data = response.read()
    except HTTPError as error:
        raise RuntimeError(f"KOSIS RSS 요청 실패 (HTTP {error.code})") from error
    except URLError as error:
        raise RuntimeError("KOSIS RSS 서버에 연결하지 못했습니다.") from error

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as error:
        raise RuntimeError("KOSIS RSS 응답이 올바른 XML 형식이 아닙니다.") from error

    notices: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        notices.append(
            {
                "title": clean_text(item.findtext("title")),
                "link": (item.findtext("link") or "").strip(),
                "published_at": (item.findtext("pubDate") or "").strip(),
                "description": clean_text(item.findtext("description")),
            }
        )
    return notices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KOSIS 공지사항 RSS 조회기")
    parser.add_argument("--limit", type=int, default=10, help="출력할 최대 건수 (기본값: 10)")
    parser.add_argument("--json", action="store_true", help="JSON을 표준 출력으로 내보냄")
    parser.add_argument("--output", type=Path, help="전체 결과를 저장할 JSON 파일 경로")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        print("--limit은 1 이상이어야 합니다.", file=sys.stderr)
        return 2

    try:
        notices = read_notices()
    except RuntimeError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1

    result = {"source": RSS_URL, "count": len(notices), "items": notices}
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{len(notices)}건을 {args.output}에 저장했습니다.")

    display_items = notices[: args.limit]
    if args.json:
        print(json.dumps({**result, "items": display_items}, ensure_ascii=False, indent=2))
    elif not args.output:
        for number, notice in enumerate(display_items, start=1):
            print(f"{number}. {notice['title']}")
            print(f"   게시일: {notice['published_at']}")
            print(f"   링크: {notice['link']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
