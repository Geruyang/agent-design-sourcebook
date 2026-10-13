from a13n_harness.media_types import is_text_media_type, text_charset


def test_text_media_types_are_text_json_xml_yaml_and_javascript() -> None:
    texts = (
        "text/csv",
        "Application/JSON; charset=utf-8",
        "application/ld+json",
        "image/svg+xml",
        "application/yaml",
        "application/javascript",
    )
    assert all(is_text_media_type(media_type) for media_type in texts)
    assert not any(is_text_media_type(media_type) for media_type in ("application/zip", "application/pdf", "image/png"))


def test_text_charset_is_the_declared_text_encoding_or_utf_8() -> None:
    assert text_charset('text/plain; Charset="GBK"') == "GBK"
    assert text_charset("text/html;charset=iso-8859-1") == "iso-8859-1"
    # No charset, an unknown one, or a codec that does not decode text.
    for content_type in ("text/plain", "text/plain; charset=no-such-charset", "text/plain; charset=zlib_codec"):
        assert text_charset(content_type) == "utf-8"
