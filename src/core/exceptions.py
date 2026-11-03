"""
CORE - Exceptions globales et transverses de l'application
"""

class AppException(Exception):
    """Exception racine de l'application."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Non autorisé"):
        super().__init__(message=message, status_code=401)

class NotFoundException(AppException):
    def __init__(self, message: str = "Ressource introuvable"):
        super().__init__(message=message, status_code=404)
