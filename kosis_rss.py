"""KOSIS 공지사항 RSS를 읽어 JSON 또는 콘솔 목록으로 출력한다.

사용 예시:
    python3 kosis_rss.py
    python3 kosis_rss.py --limit 5 --json
    python3 kosis_rss.py --output kosis_notices.json
    python3 kosis_rss.py --board-idx 2553 --rss-output notice_2553.xml
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse
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


def board_idx_from_link(link: str) -> str | None:
    """공지 링크의 boardIdx 쿼리값을 가져온다."""
    return parse_qs(urlparse(link).query).get("boardIdx", [None])[0]


def write_single_item_rss(notice: dict[str, str], output_path: Path) -> None:
    """공지 한 건을 포함한 독립적인 RSS 2.0 XML 파일을 만든다."""
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "KOSIS 공지사항 (선택 항목)"
    ET.SubElement(channel, "link").text = RSS_URL
    ET.SubElement(channel, "description").text = "KOSIS 공지사항 RSS에서 선택한 게시물"

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = notice["title"]
    ET.SubElement(item, "link").text = notice["link"]
    ET.SubElement(item, "guid", isPermaLink="true").text = notice["link"]
    ET.SubElement(item, "pubDate").text = notice["published_at"]
    ET.SubElement(item, "description").text = notice["description"]

    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KOSIS 공지사항 RSS 조회기")
    parser.add_argument("--limit", type=int, default=10, help="출력할 최대 건수 (기본값: 10)")
    parser.add_argument("--json", action="store_true", help="JSON을 표준 출력으로 내보냄")
    parser.add_argument("--output", type=Path, help="전체 결과를 저장할 JSON 파일 경로")
    parser.add_argument("--board-idx", help="다운로드할 게시물 번호 (예: 2553)")
    parser.add_argument("--rss-output", type=Path, help="선택 게시물을 저장할 RSS XML 파일 경로")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        print("--limit은 1 이상이어야 합니다.", file=sys.stderr)
        return 2
    if args.rss_output and not args.board_idx:
        print("--rss-output을 사용하려면 --board-idx를 함께 지정해야 합니다.", file=sys.stderr)
        return 2

    try:
        notices = read_notices()
    except RuntimeError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1

    result = {"source": RSS_URL, "count": len(notices), "items": notices}
    if args.rss_output:
        selected = next(
            (notice for notice in notices if board_idx_from_link(notice["link"]) == args.board_idx),
            None,
        )
        if selected is None:
            print(f"boardIdx={args.board_idx} 게시물을 RSS 목록에서 찾지 못했습니다.", file=sys.stderr)
            return 1
        write_single_item_rss(selected, args.rss_output)
        print(f"'{selected['title']}'을(를) {args.rss_output}에 RSS로 저장했습니다.")

    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{len(notices)}건을 {args.output}에 저장했습니다.")

    display_items = notices[: args.limit]
    if args.json:
        print(json.dumps({**result, "items": display_items}, ensure_ascii=False, indent=2))
    elif not args.output and not args.rss_output:
        for number, notice in enumerate(display_items, start=1):
            print(f"{number}. {notice['title']}")
            print(f"   게시일: {notice['published_at']}")
            print(f"   링크: {notice['link']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
