"""
Tests unitaires de l'algorithme RSA (domaine crypt).
"""
import pytest
from src.modules.crypt.domain.rsa import (
    mod_inverse,
    is_probable_prime,
    generate_prime,
    rsa_keypair,
    generate_keypair,
    encrypt_int,
    decrypt_int,
    encrypt_text,
    decrypt_text,
    encrypt_bytes,
    decrypt_bytes,
)


@pytest.fixture(scope="module")
def keys():
    return generate_keypair(1024)


# --- mod_inverse -----------------------------------------------------------

@pytest.mark.parametrize("e,phi", [(3, 20), (17, 3120), (65537, 3120 * 1000 + 7)])
def test_mod_inverse_matches_builtin(e, phi):
    assert mod_inverse(e, phi) == pow(e, -1, phi)


def test_mod_inverse_not_coprime():
    with pytest.raises(ValueError):
        mod_inverse(4, 20)


# --- primalité -------------------------------------------------------------

def test_is_probable_prime_small_values():
    primes = {2, 3, 5, 7, 11, 13, 97, 7919}
    for n in range(-5, 8000):
        expected = n in primes or (n > 1 and all(n % k for k in range(2, int(n ** 0.5) + 1)))
        assert is_probable_prime(n) == expected, n


def test_is_probable_prime_carmichael():
    # Nombres de Carmichael : piègent le test de Fermat, pas Miller-Rabin
    for n in (561, 1105, 1729, 2465, 2821, 6601, 8911):
        assert not is_probable_prime(n)


def test_generate_prime_has_exact_size():
    p = generate_prime(256)
    assert p.bit_length() == 256
    assert is_probable_prime(p)


# --- clés ------------------------------------------------------------------

def test_rsa_keypair_textbook_example():
    # Exemple classique : p=61, q=53 -> n=3233, phi=3120, e=17, d=2753
    (e, n), (d, n2) = rsa_keypair(61, 53)
    assert n == n2 == 3233
    assert (e * d) % 3120 == 1


def test_rsa_keypair_rejects_non_prime():
    with pytest.raises(ValueError):
        rsa_keypair(15, 53)


def test_rsa_keypair_rejects_equal_primes():
    with pytest.raises(ValueError):
        rsa_keypair(61, 61)


def test_generate_keypair_properties(keys):
    (e, n), (d, _) = keys
    assert n.bit_length() == 1024
    assert e == 65537
    assert 0 < d < n


# --- chiffrement -----------------------------------------------------------

def test_encrypt_decrypt_int_small_key():
    pub, priv = rsa_keypair(61, 53)
    for m in range(0, 3233, 37):
        assert decrypt_int(encrypt_int(m, pub), priv) == m


def test_encrypt_int_out_of_range(keys):
    pub, _ = keys
    with pytest.raises(ValueError):
        encrypt_int(pub[1], pub)


@pytest.mark.parametrize("text", [
    "Salut le monde !",
    "",
    "Accents : éèàçù — emoji 🔐",
    "x" * 5000,  # plusieurs blocs
])
def test_encrypt_decrypt_text(keys, text):
    pub, priv = keys
    blocks = encrypt_text(text, pub)
    assert decrypt_text(blocks, priv) == text


def test_leading_zero_bytes_preserved(keys):
    pub, priv = keys
    data = b"\x00\x00\x00abc\x00"
    assert decrypt_bytes(encrypt_bytes(data, pub), priv) == data


def test_wrong_key_fails(keys):
    pub, _ = keys
    _, other_priv = generate_keypair(1024)
    blocks = encrypt_text("secret", pub)
    with pytest.raises((ValueError, UnicodeDecodeError)):
        decrypt_text(blocks, other_priv)
