from enum import StrEnum


class StagingMode(StrEnum):
    IMAGE_EDIT_2D = "image_edit_2d"
    DEPTH_GUIDED_2D = "depth_guided_2d"
    RENDER_3D = "render_3d"
    HYBRID_RENDER_THEN_EDIT = "hybrid_render_then_edit"


class StagingRequestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StagingConditionType(StrEnum):
    REGION_MASK = "region_mask"
    PRODUCT_REFERENCE = "product_reference"
    SOURCE_CONCEPT = "source_concept"
    PROMPT = "prompt"
    GEOMETRY_LOCK = "geometry_lock"


class ImageEditRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class VirtualStagingOutputType(StrEnum):
    PREVIEW_IMAGE = "preview_image"
    RENDER_IMAGE = "render_image"


class EvidenceGrade(StrEnum):
    VISUAL_PREVIEW_ONLY = "visual_preview_only"
    SPATIALLY_GUIDED_PREVIEW = "spatially_guided_preview"
    FIT_VALIDATED = "fit_validated"
