class DesignDatasetError(Exception):
    """Base application error."""


class ConfigurationError(DesignDatasetError):
    """Invalid or missing configuration."""


class RulebookError(DesignDatasetError):
    """Rulebook load or validation failure."""


class ValidationPolicyError(DesignDatasetError):
    """Controlled vocabulary or business-rule failure."""


class ProviderError(DesignDatasetError):
    """Model provider failure."""

    def __init__(self, message: str, *, transient: bool = False, request_id: str | None = None):
        super().__init__(message)
        self.transient = transient
        self.request_id = request_id


class RepositoryError(DesignDatasetError):
    """Persistence failure."""


class ReviewImportError(DesignDatasetError):
    """Reviewed spreadsheet import failure."""
