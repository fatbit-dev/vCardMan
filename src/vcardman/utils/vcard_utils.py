import vobject
import base64


def get_field(card, field_name, default=""):
    """Return the string value of the first occurrence of *field_name*."""
    obj = card.contents.get(field_name.lower())
    if not obj:
        return default
    val = obj[0].value
    if isinstance(val, vobject.vcard.Name):
        return val.given + (" " + val.family if val.family else "")
    return str(val) if val else default


def get_all_fields(card, field_name):
    """Return all string values for a repeatable field."""
    objs = card.contents.get(field_name.lower(), [])
    result = []
    for obj in objs:
        val = obj.value
        result.append(str(val) if val else "")
    return result


def contact_display_name(card):
    """Best-effort display name for a vCard."""
    fn = card.contents.get("fn")
    if fn and fn[0].value:
        return fn[0].value
    n = card.contents.get("n")
    if n:
        v = n[0].value
        parts = [v.given, v.family]
        name = " ".join(p for p in parts if p)
        if name:
            return name
    return "(No Name)"


_SEARCH_FIELDS = ("fn", "org", "title", "bday", "url", "note")
_SEARCH_MULTI  = ("tel", "email", "adr")


def card_matches(card, term: str) -> bool:
    """Return True if *term* appears (case-insensitive) in any text field of *card*."""
    if not term:
        return True
    needle = term.casefold()

    for field in _SEARCH_FIELDS:
        val = get_field(card, field)
        if needle in val.casefold():
            return True

    # structured name (given + family searched individually)
    n_obj = card.contents.get("n")
    if n_obj:
        v = n_obj[0].value
        for part in (v.given or "", v.family or ""):
            if needle in part.casefold():
                return True

    for field in _SEARCH_MULTI:
        for val in get_all_fields(card, field):
            if needle in val.casefold():
                return True

    return False


def _normalize_whitespace(text: str) -> str:
    """Trim and collapse multiple spaces into single spaces."""
    return " ".join(text.split())


def clean_card_whitespace(card):
    """Normalize whitespace in all text fields of a vCard."""
    # Simple single-value text fields
    for field in ("fn", "org", "title", "bday", "url", "note"):
        objs = card.contents.get(field, [])
        for obj in objs:
            if isinstance(obj.value, str):
                obj.value = _normalize_whitespace(obj.value)

    # Structured name: trim given and family parts
    n_obj = card.contents.get("n")
    if n_obj:
        v = n_obj[0].value
        if v.given:
            v.given = _normalize_whitespace(v.given)
        if v.family:
            v.family = _normalize_whitespace(v.family)

    # Multi-value text fields (tel, email, adr, etc.)
    for field in ("tel", "email", "adr"):
        objs = card.contents.get(field, [])
        for obj in objs:
            if isinstance(obj.value, str):
                obj.value = _normalize_whitespace(obj.value)


def normalize_binary_fields(card):
    """Convert bytes values to base64 text so vobject can serialize safely."""
    for objs in card.contents.values():
        for obj in objs:
            if isinstance(obj.value, (bytes, bytearray)):
                obj.value = base64.b64encode(bytes(obj.value)).decode("ascii")
                if hasattr(obj, "params") and isinstance(obj.params, dict):
                    if "ENCODING" not in obj.params:
                        obj.params["ENCODING"] = ["BASE64"]


def get_photo_data(card) -> bytes:
    """Extract PHOTO field from vCard and return image bytes, or empty bytes if none."""
    photo_obj = card.contents.get("photo")
    if not photo_obj:
        return b""
    photo = photo_obj[0]
    val = photo.value
    if isinstance(val, bytes):
        return val
    if isinstance(val, str):
        import base64
        try:
            return base64.b64decode(val)
        except Exception:
            return b""
    return b""
