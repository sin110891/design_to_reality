from __future__ import annotations

from vision_engine.concept_board.domain.errors import BootstrapError
from vision_engine.concept_board.domain.models import ConceptBoardWorkspaceView
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin


def get_workspace_view(
    *,
    repo: ConceptBoardRepositoryMixin,
    project_id: str,
) -> ConceptBoardWorkspaceView:
    board = repo.get_concept_board_for_project(project_id)
    if board is None:
        raise BootstrapError(f"No concept board for project: {project_id}")
    directions = repo.list_directions_for_board(board.concept_board_id)
    if not directions:
        raise BootstrapError("Concept board has no directions")
    direction = directions[0]
    version = repo.get_latest_concept_version(direction.concept_direction_id)
    if version is None:
        raise BootstrapError("Concept direction has no versions")
    regions = repo.list_design_regions(direction.concept_direction_id)
    selections = repo.list_region_selections(version.concept_version_id)
    return ConceptBoardWorkspaceView(
        concept_board=board,
        concept_direction=direction,
        latest_version=version,
        regions=regions,
        selections=selections,
    )
