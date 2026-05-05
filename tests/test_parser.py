"""Tests for the secure XML parser boundary."""

from lxml import etree

from weirding._parser import make_parser


def test_make_parser_returns_xmlparser() -> None:
    """make_parser() must return an lxml XMLParser instance."""
    parser = make_parser()
    assert isinstance(parser, etree.XMLParser)


def test_xxe_entity_not_resolved() -> None:
    """XXE payloads must not be resolved — file contents must not appear in the tree."""
    xxe_payload = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b"<root>&xxe;</root>"
    )
    parser = make_parser()
    # lxml with resolve_entities=False / load_dtd=False will either parse
    # with an unresolved entity reference or raise — either outcome is safe.
    # What must NOT happen: /etc/passwd contents appearing in the serialized tree.
    try:
        tree = etree.fromstring(xxe_payload, parser=parser)
        serialized = etree.tostring(tree, encoding="unicode")
        assert "/etc/passwd" not in serialized
        assert "root:x" not in serialized  # common /etc/passwd first line
    except etree.XMLSyntaxError:
        # Raising is also acceptable — entity was not resolved
        pass


def test_billion_laughs_not_expanded() -> None:
    """Billion-laughs entity expansion must be suppressed.

    With load_dtd=False and resolve_entities=False, lxml silently ignores
    entity expansion rather than raising.  The correct assertion is that the
    parse does NOT raise AND the expanded value does NOT appear in the output.
    """
    # Build a classic billion-laughs payload:
    # &a; = "lol", &b; = "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;" (10x lol)
    # &c; references &b; 10 times, and so on up to &d;
    billion_laughs = (
        b'<?xml version="1.0"?>'
        b"<!DOCTYPE x ["
        b'<!ENTITY a "lol">'
        b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
        b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
        b'<!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">'
        b"]>"
        b"<root>&d;</root>"
    )
    parser = make_parser()
    # Must NOT raise (lxml silently suppresses with load_dtd=False)
    tree = etree.fromstring(billion_laughs, parser=parser)
    serialized = etree.tostring(tree, encoding="unicode")
    # The expanded string "lollol..." must not appear — expansion was not performed
    assert "lollol" not in serialized
