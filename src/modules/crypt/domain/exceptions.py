"""
DOMAINE - Exceptions du module Crypt
"""


class CryptoDomainException(Exception):
    pass


class KeyNotFoundError(CryptoDomainException):
    pass


class InvalidCiphertextError(CryptoDomainException):
    pass
