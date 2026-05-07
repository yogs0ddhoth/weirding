"""Tests for weirding.prompt — to_template(), format_error(), and RetryContext."""

from __future__ import annotations

from typing import Literal

import pytest
from lxml import etree
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from weirding._exceptions import ParseError
from weirding._parser import make_parser
from weirding.prompt import RetryContext, format_error, to_template

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(xml_str: str) -> etree._Element:
    """Parse an XML string with make_parser() — raises on malformed input."""
    return etree.fromstring(xml_str.encode(), make_parser())


def _comment_texts(parent: etree._Element) -> list[str]:
    """Return text content of all direct Comment children of *parent*.

    Note: in lxml, etree._Comment is a subclass of etree._Element, so a bare
    isinstance(n, etree._Element) check includes comments.  We must use
    isinstance(n, etree._Comment) to distinguish them.
    """
    return [node.text for node in parent if isinstance(node, etree._Comment)]


def _child_elements(parent: etree._Element) -> list[etree._Element]:
    """Return only true element children (not comment or PI nodes)."""
    return [
        c
        for c in parent
        if isinstance(c, etree._Element) and not isinstance(c, etree._Comment)
    ]


# ---------------------------------------------------------------------------
# 1. Scalar fields — type placeholder text
# ---------------------------------------------------------------------------


def test_scalar_str() -> None:
    class M(BaseModel):
        name: str

    out = to_template(M)
    root = _parse(out)
    assert root.find("name") is not None
    assert root.find("name").text == "string"


def test_scalar_int() -> None:
    class M(BaseModel):
        count: int

    out = to_template(M)
    root = _parse(out)
    assert root.find("count").text == "integer"


def test_scalar_float() -> None:
    class M(BaseModel):
        score: float

    out = to_template(M)
    root = _parse(out)
    assert root.find("score").text == "number"


def test_scalar_bool_uses_true_not_boolean() -> None:
    """bool fields must render as 'true', not 'boolean'."""

    class M(BaseModel):
        active: bool

    out = to_template(M)
    root = _parse(out)
    assert root.find("active").text == "true"


# ---------------------------------------------------------------------------
# 2. Description comment
# ---------------------------------------------------------------------------


def test_description_comment_appears_before_element() -> None:
    class M(BaseModel):
        name: str = Field(description="The full name")

    out = to_template(M)
    root = _parse(out)

    nodes = list(root)
    # Note: in lxml _Comment is a subclass of _Element; use _Comment directly
    comment_nodes = [n for n in nodes if isinstance(n, etree._Comment)]
    elem_nodes = _child_elements(root)

    assert len(comment_nodes) == 1
    assert "The full name" in comment_nodes[0].text
    assert len(elem_nodes) == 1
    assert elem_nodes[0].tag == "name"

    # Comment must appear before the element in document order
    comment_idx = nodes.index(comment_nodes[0])
    elem_idx = nodes.index(elem_nodes[0])
    assert comment_idx < elem_idx


# ---------------------------------------------------------------------------
# 3. Optional field
# ---------------------------------------------------------------------------


def test_optional_field_has_optional_comment() -> None:
    class M(BaseModel):
        bio: str | None = None

    out = to_template(M)
    root = _parse(out)

    comments = _comment_texts(root)
    assert any("optional" in c for c in comments)
    assert root.find("bio") is not None
    assert root.find("bio").text == "string"


def test_optional_field_pipe_syntax() -> None:
    """Test Python 3.10+ X | None syntax is treated as optional."""

    class M(BaseModel):
        notes: str | None = None

    out = to_template(M)
    root = _parse(out)

    comments = _comment_texts(root)
    assert any("optional" in c for c in comments)
    assert root.find("notes").text == "string"


# ---------------------------------------------------------------------------
# 4. Optional field with description — description first, optional second
# ---------------------------------------------------------------------------


def test_optional_with_description_order() -> None:
    class M(BaseModel):
        memo: str | None = Field(default=None, description="A short note")

    out = to_template(M)
    root = _parse(out)

    nodes = list(root)
    comment_nodes = [n for n in nodes if isinstance(n, etree._Comment)]

    assert len(comment_nodes) >= 2
    # description comment must appear before optional comment
    desc_idx = next(
        i
        for i, n in enumerate(nodes)
        if isinstance(n, etree._Comment) and "A short note" in n.text
    )
    opt_idx = next(
        i
        for i, n in enumerate(nodes)
        if isinstance(n, etree._Comment) and "optional" in n.text
    )
    assert desc_idx < opt_idx


# ---------------------------------------------------------------------------
# 5. Enum (Literal) field
# ---------------------------------------------------------------------------


def test_literal_field_allowed_values_comment() -> None:
    class M(BaseModel):
        status: Literal["pending", "confirmed", "shipped"]

    out = to_template(M)
    root = _parse(out)

    comments = _comment_texts(root)
    allowed_comments = [c for c in comments if "allowed values" in c]
    assert len(allowed_comments) == 1

    comment_text = allowed_comments[0]
    assert "pending" in comment_text
    assert "confirmed" in comment_text
    assert "shipped" in comment_text

    # Element should be rendered as a scalar placeholder
    assert root.find("status") is not None
    assert root.find("status").text == "string"


def test_literal_field_optional() -> None:
    class M(BaseModel):
        priority: Literal["low", "high"] | None = None

    out = to_template(M)
    root = _parse(out)

    comments = _comment_texts(root)
    assert any("optional" in c for c in comments)
    assert any("allowed values" in c for c in comments)
    assert root.find("priority") is not None


# ---------------------------------------------------------------------------
# 6. Nested object field
# ---------------------------------------------------------------------------


def test_nested_object_recurses() -> None:
    class Address(BaseModel):
        street: str
        city: str

    class M(BaseModel):
        address: Address

    out = to_template(M)
    root = _parse(out)

    addr_elem = root.find("address")
    assert addr_elem is not None

    assert addr_elem.find("street") is not None
    assert addr_elem.find("street").text == "string"
    assert addr_elem.find("city") is not None
    assert addr_elem.find("city").text == "string"


# ---------------------------------------------------------------------------
# 7. List of scalars
# ---------------------------------------------------------------------------


def test_list_of_scalars_two_items_and_comment() -> None:
    class M(BaseModel):
        tags: list[str]

    out = to_template(M)
    root = _parse(out)

    wrapper = root.find("tags")
    assert wrapper is not None

    # Two child item elements (exclude comment nodes)
    children = _child_elements(wrapper)
    assert len(children) == 2
    assert all(c.text == "string" for c in children)

    # "repeat as needed" comment inside wrapper
    wrapper_comments = [n.text for n in wrapper if isinstance(n, etree._Comment)]
    assert any("repeat as needed" in c for c in wrapper_comments)


def test_list_item_tag_strips_trailing_s() -> None:
    """Default singularization: field 'tags' → item tag 'tag'."""

    class M(BaseModel):
        tags: list[str]

    out = to_template(M)
    root = _parse(out)

    wrapper = root.find("tags")
    children = _child_elements(wrapper)
    assert all(c.tag == "tag" for c in children)


def test_list_item_tag_no_s_uses_item() -> None:
    """Field name without trailing 's' → item tag 'item'."""

    class M(BaseModel):
        data: list[int]

    out = to_template(M)
    root = _parse(out)

    wrapper = root.find("data")
    children = _child_elements(wrapper)
    assert all(c.tag == "item" for c in children)
    assert all(c.text == "integer" for c in children)


# ---------------------------------------------------------------------------
# 8. List of objects
# ---------------------------------------------------------------------------


def test_list_of_objects_two_items_with_sub_structure() -> None:
    class LineItem(BaseModel):
        product_id: str
        quantity: int

    class M(BaseModel):
        items: list[LineItem]

    out = to_template(M)
    root = _parse(out)

    wrapper = root.find("items")
    assert wrapper is not None

    children = _child_elements(wrapper)
    assert len(children) == 2

    for child in children:
        assert child.tag == "item"
        assert child.find("product_id") is not None
        assert child.find("product_id").text == "string"
        assert child.find("quantity") is not None
        assert child.find("quantity").text == "integer"


# ---------------------------------------------------------------------------
# 9. Optional list field
# ---------------------------------------------------------------------------


def test_optional_list_has_optional_comment_before_wrapper() -> None:
    class M(BaseModel):
        notes: list[str] | None = None

    out = to_template(M)
    root = _parse(out)

    nodes = list(root)

    opt_idx = next(
        (
            i
            for i, n in enumerate(nodes)
            if isinstance(n, etree._Comment) and "optional" in n.text
        ),
        None,
    )
    wrapper_idx = next(
        (
            i
            for i, n in enumerate(nodes)
            if isinstance(n, etree._Element) and n.tag == "notes"
        ),
        None,
    )

    assert opt_idx is not None, "expected <!-- optional --> comment"
    assert wrapper_idx is not None, "expected <notes> wrapper element"
    assert opt_idx < wrapper_idx, "optional comment must precede wrapper element"


# ---------------------------------------------------------------------------
# 10. Root tag equals model.__name__
# ---------------------------------------------------------------------------


def test_root_tag_equals_model_name() -> None:
    class MyDocument(BaseModel):
        title: str

    out = to_template(MyDocument)
    root = _parse(out)
    assert root.tag == "MyDocument"


def test_root_tag_different_model() -> None:
    class Invoice(BaseModel):
        amount: float

    out = to_template(Invoice)
    root = _parse(out)
    assert root.tag == "Invoice"


# ---------------------------------------------------------------------------
# 11. Well-formed XML — make_parser() must not raise
# ---------------------------------------------------------------------------


def test_output_is_well_formed_xml_simple() -> None:
    class M(BaseModel):
        name: str
        age: int

    out = to_template(M)
    # Should not raise
    _parse(out)


def test_output_is_well_formed_xml_complex() -> None:
    """Complex model with optional, list, nested, and Literal fields."""

    class LineItem(BaseModel):
        product_id: str
        quantity: int

    class Order(BaseModel):
        order_id: str
        customer_name: str = Field(description="The customer's full name.")
        status: Literal["pending", "confirmed", "shipped"]
        notes: str | None = None
        items: list[LineItem]

    out = to_template(Order)
    # Should not raise
    _parse(out)


# ---------------------------------------------------------------------------
# 12. Multi-field model — verify all fields appear
# ---------------------------------------------------------------------------


def test_all_fields_present() -> None:
    class M(BaseModel):
        a: str
        b: int
        c: float
        d: bool

    out = to_template(M)
    root = _parse(out)

    assert root.find("a").text == "string"
    assert root.find("b").text == "integer"
    assert root.find("c").text == "number"
    assert root.find("d").text == "true"


# ---------------------------------------------------------------------------
# 13. define_model() integration — pipeline produces valid template
# ---------------------------------------------------------------------------


def test_define_model_integration() -> None:
    """to_template() works on a model produced by the full define_model() pipeline."""
    from weirding import define_model

    xml_schema = "<Order><order_id /><items type='array'><item /></items></Order>"
    Model = define_model(xml_schema)
    out = to_template(Model)
    root = _parse(out)

    assert root.tag == "Order"
    assert root.find("order_id") is not None

    items_elem = root.find("items")
    assert items_elem is not None
    # Two item children rendered (exclude comment nodes)
    children = _child_elements(items_elem)
    assert len(children) == 2
    assert all(c.tag == "item" for c in children)


# ===========================================================================
# Phase B — format_error() and RetryContext
# ===========================================================================

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


class _Simple(BaseModel):
    name: str


class _Typed(BaseModel):
    count: int


class _Forbidden(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


class _Constrained(BaseModel):
    score: int = Field(gt=0)


class _MultiRequired(BaseModel):
    first: str
    second: str


class _Inner(BaseModel):
    value: str


class _Outer(BaseModel):
    inner: _Inner


class _WithList(BaseModel):
    items: list[_Inner]


# ---------------------------------------------------------------------------
# format_error — test 1: missing required field
# ---------------------------------------------------------------------------


def test_format_error_missing_required_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Simple.model_validate({})
    ve = exc_info.value

    result = format_error(ve, model=_Simple)

    assert "name" in result
    assert "Field required" in result


# ---------------------------------------------------------------------------
# format_error — test 2: wrong type
# ---------------------------------------------------------------------------


def test_format_error_wrong_type() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Typed.model_validate({"count": "not-a-number"})
    ve = exc_info.value

    result = format_error(ve, model=_Typed)

    assert "count" in result
    # Pydantic v2 reports something like "Input should be a valid integer"
    assert "int" in result.lower() or "integer" in result.lower()


# ---------------------------------------------------------------------------
# format_error — test 3: extra field forbidden
# ---------------------------------------------------------------------------


def test_format_error_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Forbidden.model_validate({"name": "ok", "extra_key": "val"})
    ve = exc_info.value

    result = format_error(ve, model=_Forbidden)

    assert "Extra inputs" in result or "extra_key" in result


# ---------------------------------------------------------------------------
# format_error — test 4: constraint violation
# ---------------------------------------------------------------------------


def test_format_error_constraint_violation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Constrained.model_validate({"score": -1})
    ve = exc_info.value

    result = format_error(ve, model=_Constrained)

    assert "score" in result
    assert "greater than" in result


# ---------------------------------------------------------------------------
# format_error — test 5: ParseError wrapping ValidationError
# ---------------------------------------------------------------------------


def test_format_error_parse_error_wrapping_validation_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Simple.model_validate({})
    ve = exc_info.value

    # Construct ParseError with __cause__ set to the ValidationError
    pe = ParseError("msg")
    pe.__cause__ = ve

    result_direct = format_error(ve, model=_Simple)
    result_wrapped = format_error(pe, model=_Simple)

    assert result_direct == result_wrapped


# ---------------------------------------------------------------------------
# format_error — test 6: ParseError without ValidationError cause
# ---------------------------------------------------------------------------


def test_format_error_parse_error_without_validation_cause() -> None:
    pe = ParseError("raw xml parse failure")
    # __cause__ is None by default

    result = format_error(pe, model=_Simple)

    assert "Unexpected error" in result


# ---------------------------------------------------------------------------
# format_error — test 7: non-ValidationError exception
# ---------------------------------------------------------------------------


def test_format_error_non_validation_error() -> None:
    result = format_error(ValueError("boom"), model=_Simple)

    assert "Unexpected error" in result


# ---------------------------------------------------------------------------
# format_error — test 8: multiple errors — header count correct
# ---------------------------------------------------------------------------


def test_format_error_multiple_errors() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _MultiRequired.model_validate({})
    ve = exc_info.value

    result = format_error(ve, model=_MultiRequired)

    assert "first" in result
    assert "second" in result
    assert "2 validation errors" in result


# ---------------------------------------------------------------------------
# format_error — test 9: nested field path (dot notation)
# ---------------------------------------------------------------------------


def test_format_error_nested_field_path() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Outer.model_validate({"inner": {}})
    ve = exc_info.value

    result = format_error(ve, model=_Outer)

    # Path must be in dot notation: inner.value
    assert "inner.value" in result


# ---------------------------------------------------------------------------
# format_error — test 10: list item path (bracket notation)
# ---------------------------------------------------------------------------


def test_format_error_list_item_path() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _WithList.model_validate({"items": [{}]})
    ve = exc_info.value

    result = format_error(ve, model=_WithList)

    # Path must include bracket notation: items[0].value
    assert "items[0].value" in result


# ---------------------------------------------------------------------------
# format_error — test 11: privacy guard — no raw XML in output
# ---------------------------------------------------------------------------


def test_format_error_privacy_no_raw_input_in_output() -> None:
    """Verify that raw input values (PII risk) are not echoed in the error message.

    include_input=False is set in format_error(); this test is a regression barrier.
    If that flag is ever removed, this test will fail.
    """
    from weirding import parse

    # Use clearly identifiable content unlikely to appear in generic error messages
    xml_with_pii = "<_Simple><name>SENTINEL_PII_VALUE_12345</name></_Simple>"

    # Parse against a model that has extra="forbid" to trigger a ValidationError
    # that would normally echo back the input fields
    class _StrictSimple(BaseModel):
        model_config = ConfigDict(extra="forbid")
        required_field: str

    try:
        parse(xml_with_pii.replace("_Simple", "_StrictSimple"), _StrictSimple)
    except ParseError as exc:
        result = format_error(exc, model=_StrictSimple)
        assert "SENTINEL_PII_VALUE_12345" not in result
    except Exception:
        # If parse fails for another reason, use a direct ValidationError
        with pytest.raises(ValidationError) as exc_info:
            _StrictSimple.model_validate({"name": "SENTINEL_PII_VALUE_12345"})
        ve = exc_info.value
        result = format_error(ve, model=_StrictSimple)
        assert "SENTINEL_PII_VALUE_12345" not in result


# ===========================================================================
# RetryContext tests
# ===========================================================================

# ---------------------------------------------------------------------------
# RetryContext — test 12: initial state
# ---------------------------------------------------------------------------


def test_retry_context_initial_state() -> None:
    ctx = RetryContext(_Simple)

    assert ctx.attempt == 0
    assert ctx.exceeded is False


# ---------------------------------------------------------------------------
# RetryContext — test 13: after one error
# ---------------------------------------------------------------------------


def test_retry_context_after_one_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Simple.model_validate({})
    ve = exc_info.value

    ctx = RetryContext(_Simple)
    ctx.record_error(ve)

    assert ctx.attempt == 1
    msg = ctx.retry_message()
    assert msg != ""
    assert "name" in msg


# ---------------------------------------------------------------------------
# RetryContext — test 14: exceeded after max_attempts
# ---------------------------------------------------------------------------


def test_retry_context_exceeded_after_max_attempts() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Simple.model_validate({})
    ve = exc_info.value

    ctx = RetryContext(_Simple, max_attempts=3)
    for _ in range(3):
        ctx.record_error(ve)

    assert ctx.exceeded is True


# ---------------------------------------------------------------------------
# RetryContext — test 15: retry_message before record_error returns empty string
# ---------------------------------------------------------------------------


def test_retry_context_retry_message_before_record_error() -> None:
    ctx = RetryContext(_Simple)

    assert ctx.retry_message() == ""


# ---------------------------------------------------------------------------
# RetryContext — test 16: custom max_attempts
# ---------------------------------------------------------------------------


def test_retry_context_custom_max_attempts() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Simple.model_validate({})
    ve = exc_info.value

    ctx = RetryContext(_Simple, max_attempts=1)
    ctx.record_error(ve)

    assert ctx.exceeded is True


# ---------------------------------------------------------------------------
# RetryContext — test 17: end-to-end integration with define_model / parse
# ---------------------------------------------------------------------------


def test_retry_context_end_to_end_integration() -> None:
    """Full pipeline: define_model, parse invalid XML, RetryContext, retry_message."""
    from weirding import define_model, parse

    xml_schema = "<Person><name /></Person>"
    PersonModel = define_model(xml_schema)

    # XML missing the required <name> field
    bad_xml = "<Person></Person>"

    exc: Exception | None = None
    try:
        parse(bad_xml, PersonModel)
    except ParseError as caught:
        exc = caught

    assert exc is not None, "parse() should have raised ParseError"

    ctx = RetryContext(PersonModel)
    ctx.record_error(exc)

    msg = ctx.retry_message()
    assert msg != ""
    assert "name" in msg
