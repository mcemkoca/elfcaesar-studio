import math
import re

from studio_ui import leaks, pwgen
from studio_ui.pwgen import Policy


def test_random_has_every_class_and_length():
    for _ in range(200):
        pw = pwgen.generate(Policy(length=16))
        assert len(pw) == 16
        assert re.search(r"[a-z]", pw) and re.search(r"[A-Z]", pw) and re.search(r"\d", pw)
        assert any(c in pwgen.SYMBOLS for c in pw)
        assert pw[0] not in pwgen.SYMBOLS
        assert not set(pw) & set("Il1O0o")


def test_unique_and_not_leaked():
    seen = {pwgen.generate(Policy(length=12)) for _ in range(300)}
    assert len(seen) == 300
    assert all(leaks.check(p) is None for p in list(seen)[:50])


def test_pin_and_syllable():
    for _ in range(100):
        pin = pwgen.generate(Policy(mode="pin", length=6))
        assert pin.isdigit() and len(pin) == 6 and len(set(pin)) > 1
    s = pwgen.generate(Policy(mode="syllable", groups=4))
    assert re.fullmatch(r"([a-zA-Z]{4}-){4}\d{2}", s), s
    assert any(c.isupper() for c in s)


def test_entropy_exact():
    p = Policy(length=20, avoid_ambiguous=False, symbol_set=pwgen.SYMBOLS)
    n = 26 + 26 + 10 + len(pwgen.SYMBOLS)
    assert abs(pwgen.entropy_bits(p) - 20 * math.log2(n)) < 1e-9
    assert pwgen.entropy_bits(Policy(mode="syllable", groups=4)) > 50
    assert abs(pwgen.entropy_bits(Policy(mode="pin", length=6)) - 6 * math.log2(10)) < 1e-9


def test_passwordrules_and_site_policy():
    r = pwgen.parse_passwordrules("minlength: 8; maxlength: 12; required: lower; required: upper; "
                                  "required: digit; allowed: [-_!]")
    assert r["maxlength"] == 12 and r["minlength"] == 8 and set(r["required"]) == {"lower", "upper", "digits"}
    p = pwgen.policy_for_site(Policy(length=20), passwordrules="maxlength: 12; required: lower, upper; "
                                                                "required: digit; allowed: [-_!]")
    for _ in range(100):
        pw = pwgen.generate(p)
        assert len(pw) == 12
        assert set(pw) <= set(pwgen.LOWER + pwgen.UPPER + pwgen.DIGITS + "-_!")
    pin = pwgen.policy_for_site(Policy(), maxlength=6, pattern=r"\d{6}")
    assert pin.mode == "pin" and pwgen.generate(pin).isdigit() and len(pwgen.generate(pin)) == 6
    only_digits = pwgen.policy_for_site(Policy(), passwordrules="required: digit; maxlength: 4")
    assert only_digits.mode == "pin" and len(pwgen.generate(only_digits)) == 4
    m = pwgen.policy_for_site(Policy(length=30), maxlength="16")
    assert len(pwgen.generate(m)) == 16


def test_bad_inputs_are_clamped():
    p = Policy(length=3, lower=False, upper=False, digits=False, symbols=False).clamp()
    assert p.length >= 8 and p.lower
    assert pwgen.policy_for_site(maxlength="abc").length == 20
    assert len(pwgen.generate(Policy(length=500))) == 128


def test_change_password_url():
    assert pwgen.change_password_url("https://accounts.example.com/login") == \
        "https://accounts.example.com/.well-known/change-password"
    assert pwgen.change_password_url("") == ""
