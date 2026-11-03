"""
DOMAINE - Algorithme RSA (implémentation pédagogique, "textbook RSA")
Pur Python, aucune dépendance externe.

Attention : sans padding (OAEP), le RSA textbook est déterministe et malléable.
À ne pas utiliser tel quel en production.
"""
import secrets
from math import gcd

DEFAULT_E = 65537

# Petits premiers pour éliminer rapidement les candidats évidents.
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71)


# ---------------------------------------------------------------------------
# Arithmétique
# ---------------------------------------------------------------------------

def mod_inverse(e: int, phi: int) -> int:
    """Inverse modulaire par l'algorithme d'Euclide étendu.

    Retourne d dans [0, phi) tel que (e * d) % phi == 1.
    Lève ValueError si e et phi ne sont pas premiers entre eux.
    """
    u0, u1 = 1, 0
    a, b = e, phi
    while b:
        q = a // b
        a, b = b, a - q * b
        u0, u1 = u1, u0 - q * u1
    # En fin de boucle, a = pgcd(e, phi)
    if a != 1:
        raise ValueError(f"e={e} and phi={phi} are not coprime")
    return u0 % phi


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    """Test de primalité de Miller-Rabin (probabilité d'erreur <= 4^-rounds)."""
    if n < 2:
        return False
    for sp in _SMALL_PRIMES:
        if n % sp == 0:
            return n == sp

    # n - 1 = 2^r * s avec s impair
    r, s = 0, n - 1
    while s % 2 == 0:
        r += 1
        s //= 2

    for _ in range(rounds):
        a = 2 + secrets.randbelow(n - 3)  # a dans [2, n-2]
        x = pow(a, s, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False  # a est un témoin : n est composé
    return True


def generate_prime(bits: int) -> int:
    """Génère un nombre premier aléatoire d'exactement `bits` bits."""
    if bits < 8:
        raise ValueError("bits must be >= 8")
    while True:
        # Bit de poids fort forcé (taille exacte) + bit de poids faible (impair)
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if is_probable_prime(candidate):
            return candidate


# ---------------------------------------------------------------------------
# Génération de clés
# ---------------------------------------------------------------------------

def rsa_keypair(p: int, q: int):
    """Construit une paire de clés à partir de deux premiers distincts.

    Retourne ((e, n), (d, n)) : clé publique, clé privée.
    """
    if p == q:
        raise ValueError("p and q must be distinct primes")
    if not (is_probable_prime(p) and is_probable_prime(q)):
        raise ValueError("p and q must both be prime")

    n = p * q
    phi = (p - 1) * (q - 1)

    if phi > DEFAULT_E:
        # Cas normal : 65537, ou le prochain impair premier avec phi (cas rare).
        e = DEFAULT_E
        while gcd(e, phi) != 1:
            e += 2
    else:
        # Petits p, q (exercices / tests) : plus petit e impair premier avec phi.
        # phi est pair et phi-1 est toujours premier avec phi, la boucle termine.
        e = 3
        while gcd(e, phi) != 1:
            e += 2

    d = mod_inverse(e, phi)
    return (e, n), (d, n)


def generate_keypair(bits: int = 2048):
    """Génère une paire de clés RSA dont le module n fait `bits` bits."""
    if bits < 16:
        raise ValueError("bits must be >= 16")
    while True:
        p = generate_prime(bits // 2)
        q = generate_prime(bits - bits // 2)
        if p != q and (p * q).bit_length() == bits:
            try:
                return rsa_keypair(p, q)
            except ValueError:
                continue  # gcd(e, phi) != 1 sans solution simple : on recommence


# ---------------------------------------------------------------------------
# Chiffrement / déchiffrement d'entiers
# ---------------------------------------------------------------------------

def encrypt_int(m: int, public_key) -> int:
    """c = m^e mod n"""
    e, n = public_key
    if not 0 <= m < n:
        raise ValueError("message must satisfy 0 <= m < n")
    return pow(m, e, n)


def decrypt_int(c: int, private_key) -> int:
    """m = c^d mod n"""
    d, n = private_key
    if not 0 <= c < n:
        raise ValueError("ciphertext must satisfy 0 <= c < n")
    return pow(c, d, n)


# ---------------------------------------------------------------------------
# Chiffrement / déchiffrement de texte (découpage en blocs)
# ---------------------------------------------------------------------------

def _block_size(n: int) -> int:
    """Nombre d'octets utiles par bloc.

    Chaque bloc est préfixé d'un octet 0x01 pour conserver les zéros de tête,
    et l'entier obtenu doit rester strictement inférieur à n.
    """
    size = (n.bit_length() - 1) // 8 - 1
    if size < 1:
        raise ValueError("modulus too small to encrypt bytes")
    return size


def encrypt_bytes(data: bytes, public_key) -> list[int]:
    """Chiffre des octets bloc par bloc. Retourne la liste des blocs chiffrés."""
    _, n = public_key
    size = _block_size(n)
    blocks = []
    for i in range(0, len(data), size):
        chunk = b"\x01" + data[i:i + size]
        blocks.append(encrypt_int(int.from_bytes(chunk, "big"), public_key))
    return blocks


def decrypt_bytes(blocks: list[int], private_key) -> bytes:
    """Déchiffre une liste de blocs produite par encrypt_bytes."""
    out = bytearray()
    for c in blocks:
        m = decrypt_int(c, private_key)
        chunk = m.to_bytes((m.bit_length() + 7) // 8, "big")
        if not chunk or chunk[0] != 0x01:
            raise ValueError("invalid block (wrong key or corrupted data)")
        out += chunk[1:]
    return bytes(out)


def encrypt_text(text: str, public_key) -> list[int]:
    return encrypt_bytes(text.encode("utf-8"), public_key)


def decrypt_text(blocks: list[int], private_key) -> str:
    return decrypt_bytes(blocks, private_key).decode("utf-8")
