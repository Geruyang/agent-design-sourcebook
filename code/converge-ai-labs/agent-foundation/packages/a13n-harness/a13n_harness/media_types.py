"""Media type facts shared by Harness content paths and their Hosts."""

# Text types outside `text/*`; the `+json` and `+xml` structured syntax suffixes are text too.
_TEXT_TYPES = frozenset(
    {"application/json", "application/xml", "application/yaml", "application/x-yaml", "application/javascript"}
)


def is_text_media_type(media_type: str) -> bool:
    """Whether content of `media_type` is text: `text/*`, JSON, XML, YAML, JavaScript and the `+json` and `+xml`
    suffixes. Parameters and case are ignored."""
    canonical = media_type.partition(";")[0].strip().casefold()
    return canonical.startswith("text/") or canonical in _TEXT_TYPES or canonical.endswith(("+json", "+xml"))


def text_charset(content_type: str) -> str:
    """The text encoding a `Content-Type` value declares, or UTF-8 when it declares none that decodes text."""
    for parameter in content_type.split(";")[1:]:
        key, separator, value = parameter.partition("=")
        if separator and key.strip().casefold() == "charset":
            charset = value.strip().strip('"')
            try:
                # Decoding nothing skips the lookup; unknown names and codecs that do not decode bytes to text raise.
                b"\x00".decode(charset, errors="replace")
            except (LookupError, UnicodeError):
                break
            return charset
    return "utf-8"


__all__ = ["is_text_media_type", "text_charset"]
