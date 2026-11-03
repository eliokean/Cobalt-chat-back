"""
DOMAINE - Exceptions métier du module Auth
"""


class AuthDomainException(Exception):
    pass


class InvalidUsernameError(AuthDomainException):
    pass


class WeakPasswordError(AuthDomainException):
    pass


class UsernameTakenError(AuthDomainException):
    pass


class InvalidCredentialsError(AuthDomainException):
    pass
