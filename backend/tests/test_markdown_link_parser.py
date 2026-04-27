from app.services.markdown_link_parser import parse_wiki_links


def test_parse_wiki_links_extracts_unique_trimmed_titles() -> None:
    markdown = "See [[ Search Design ]] and [[Search Design]] then [[Backlinks]]."

    assert parse_wiki_links(markdown) == ["Search Design", "Backlinks"]


def test_parse_wiki_links_ignores_escaped_and_empty_links() -> None:
    markdown = r"Ignore \[[Escaped]] and [[ ]] but keep [[Real Note]]."

    assert parse_wiki_links(markdown) == ["Real Note"]
