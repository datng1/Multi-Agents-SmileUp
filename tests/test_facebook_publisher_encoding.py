from urllib.parse import parse_qs

from tools.facebook_publisher import _encode_graph_form, format_facebook_message


def _bad_decode_once(text: str) -> str:
    return text.encode("utf-8").decode("latin1")


def main() -> None:
    draft = {
        "title": "SmileUp - b\u00e0i \u0111\u0103ng ki\u1ec3m tra h\u1ec7 th\u1ed1ng",
        "body": (
            "B\u00e1c s\u0129 t\u01b0 v\u1ea5n r\u0103ng s\u1ee9, ph\u1ee5c h\u00ecnh "
            "v\u00e0 c\u1ea5y implant ph\u00f9 h\u1ee3p t\u1eebng t\u00ecnh tr\u1ea1ng."
        ),
        "call_to_action": "\u0110\u1ec3 l\u1ea1i S\u0110T \u0111\u1ec3 SmileUp g\u1ecdi l\u1ea1i t\u01b0 v\u1ea5n.",
        "hashtags": ["#SmileUp", "#R\u0103ngS\u1ee9", "#C\u1ea5yImplant"],
    }
    message = format_facebook_message(draft)
    assert "b\u00e0i \u0111\u0103ng ki\u1ec3m tra h\u1ec7 th\u1ed1ng" in message
    assert "B\u00e1c s\u0129 t\u01b0 v\u1ea5n r\u0103ng s\u1ee9" in message
    assert "\u0110\u1ec3 l\u1ea1i S\u0110T" in message
    assert "#R\u0103ngS\u1ee9" in message
    assert "?" not in message

    encoded = _encode_graph_form({"message": message, "access_token": "token"})
    decoded = parse_qs(encoded.decode("ascii"), encoding="utf-8", errors="strict")
    assert decoded["message"][0] == message

    mojibake_once = {key: _bad_decode_once(value) if isinstance(value, str) else value for key, value in draft.items()}
    mojibake_once["hashtags"] = [_bad_decode_once(tag) for tag in draft["hashtags"]]
    repaired_once = format_facebook_message(mojibake_once)
    assert repaired_once == message
    assert "\u00c3" not in repaired_once

    mojibake_twice = {key: _bad_decode_once(value) if isinstance(value, str) else value for key, value in mojibake_once.items()}
    mojibake_twice["hashtags"] = [_bad_decode_once(tag) for tag in mojibake_once["hashtags"]]
    repaired_twice = format_facebook_message(mojibake_twice)
    assert repaired_twice == message
    assert "\u00c3" not in repaired_twice

    print("FACEBOOK ENCODING OK")


if __name__ == "__main__":
    main()
