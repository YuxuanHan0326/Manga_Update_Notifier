from app.services.text_normalization import repair_mojibake_text


def _garbled_utf8(text: str) -> str:
    return text.encode("utf-8").decode("latin-1")


def test_repair_mojibake_text_recovers_garbled_chinese():
    assert repair_mojibake_text(_garbled_utf8("海贼王")) == "海贼王"
    assert repair_mojibake_text(_garbled_utf8("第1176话")) == "第1176话"


def test_repair_mojibake_text_keeps_normal_text_unchanged():
    assert repair_mojibake_text("海贼王") == "海贼王"
    assert repair_mojibake_text("Webhook Test") == "Webhook Test"
