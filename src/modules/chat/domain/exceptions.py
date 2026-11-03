"""
DOMAINE - Exceptions Métier
Définit les erreurs spécifiques aux règles de gestion du domaine.
"""


class DomainException(Exception):
    """Exception de base du domaine."""
    pass


class EmptyMessageError(DomainException):
    pass


class MessageTooLongError(DomainException):
    pass


class DiscussionNotFoundError(DomainException):
    pass


class MessageNotFoundError(DomainException):
    pass


class NotAMemberError(DomainException):
    pass


class InvalidDiscussionError(DomainException):
    pass


class InvalidReactionError(DomainException):
    pass
