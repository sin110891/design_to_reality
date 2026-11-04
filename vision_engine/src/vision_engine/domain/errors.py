from __future__ import annotations


class VisionEngineError(Exception):
    """Base error for the vision engine."""


class ConfigurationError(VisionEngineError):
    """Invalid or missing configuration."""


class ValidationError(VisionEngineError):
    """Schema or business-rule validation failure."""


class ProviderError(VisionEngineError):
    """Upstream model / embedding provider failure."""

    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.transient = transient


class EmptyRetrievalError(VisionEngineError):
    """No curated references matched the query."""


class ImageError(VisionEngineError):
    """Invalid or unsupported image input."""


class EmbeddingSpaceError(VisionEngineError):
    """Embedding vector incompatible with the target index space."""


class SnapshotError(VisionEngineError):
    """Dataset snapshot is invalid or not in the required state."""


class IndexBuildError(VisionEngineError):
    """Vector index build or validation failed."""


class IndexPromotionError(VisionEngineError):
    """Index promotion gate failed or alias update rejected."""
