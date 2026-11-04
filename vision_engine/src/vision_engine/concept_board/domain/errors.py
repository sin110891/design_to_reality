from vision_engine.domain.errors import VisionEngineError


class ConceptBoardError(VisionEngineError):
    """Base error for concept board workflows."""


class BootstrapError(ConceptBoardError):
    """Failed to bootstrap a concept board from Vision Engine output."""


class CatalogueError(ConceptBoardError):
    """Catalogue import or snapshot error."""


class RegionError(ConceptBoardError):
    """Design region or geometry error."""


class RetrievalError(ConceptBoardError):
    """Product retrieval error."""


class SelectionError(ConceptBoardError):
    """Region selection or approval error."""


class ProcurementError(ConceptBoardError):
    """Procurement schedule error."""


class InvariantError(ConceptBoardError):
    """Data invariant violation."""
