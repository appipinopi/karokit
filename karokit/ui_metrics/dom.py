from __future__ import annotations

from html.parser import HTMLParser


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs):
        if tag != "meta":
            return
        mapping = dict(attrs)
        key = mapping.get("name") or mapping.get("property")
        content = mapping.get("content")
        if key and content:
            self.meta[key] = content


def extract_meta(html: str) -> dict[str, str]:
    parser = _MetaParser()
    parser.feed(html)
    return parser.meta
