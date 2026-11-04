from vision_engine.domain.errors import VisionEngineError


class CatalogProviderError(VisionEngineError):
    """External catalogue provider error."""


class Channel3Error(CatalogProviderError):
    """Channel3 API error."""
