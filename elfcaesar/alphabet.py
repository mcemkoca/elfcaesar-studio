"""Turkish alphabet: the single source of truth."""
ALPHABET = "abcçdefgğhıijklmnoöprsştuüvyz"
N = len(ALPHABET)
CHAR_TO_IDX = {c: i for i, c in enumerate(ALPHABET)}
assert N == 29 and len(CHAR_TO_IDX) == N
