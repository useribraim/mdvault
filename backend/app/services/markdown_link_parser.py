import re

LINK_PATTERN = re.compile(r"(?<!\\)\[\[([^\[\]\r\n]+)\]\]")


def parse_wiki_links(markdown: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()

    for match in LINK_PATTERN.finditer(markdown):
        raw_title = match.group(1).strip()
        if not raw_title or len(raw_title) > 255:
            continue

        normalized_title = raw_title.lower()
        if normalized_title in seen:
            continue

        seen.add(normalized_title)
        titles.append(raw_title)

    return titles
