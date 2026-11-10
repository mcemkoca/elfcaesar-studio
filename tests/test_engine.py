import pytest
from elfcaesar.engine import *
from elfcaesar.alphabet import ALPHABET, N

def test_alphabet(): assert N == 29 and len(set(ALPHABET)) == 29
@pytest.mark.parametrize("shift", range(29))
def test_roundtrip(shift):
    sample = "Merhaba Dünya! ÇĞİŞÖÜ 123\nTire - altçizgi_ boru | tilde ~"
    assert decode(encode(sample, shift), shift) == sample
def test_bad_token():
    with pytest.raises(ElfFormatError): elf_decode("zzz")
def test_bruteforce_count(): assert len(brute_force(encode("test", 8))) == 29
