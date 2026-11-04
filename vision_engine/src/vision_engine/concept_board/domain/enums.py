from enum import StrEnum


class ConceptBoardStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConceptDirectionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConceptVersionStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    UNDER_REVIEW = "under_review"
    CLIENT_APPROVED = "client_approved"
    ARCHITECT_APPROVED = "architect_approved"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ConceptAssetType(StrEnum):
    PRIMARY_RENDER = "primary_render"
    THUMBNAIL = "thumbnail"
    COMPARISON = "comparison"


class DesignRegionLifecycle(StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    RETIRED = "retired"


class RegionGeometryType(StrEnum):
    POLYGON = "polygon"
    BOUNDING_BOX = "bounding_box"
    SEGMENTATION_MASK = "segmentation_mask"
    SURFACE_MAP = "surface_map"


class RequirementSeverity(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    PREFERENCE = "preference"


class CatalogueSnapshotStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    SEALED = "sealed"
    DEPRECATED = "deprecated"


class ProductLifecycle(StrEnum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    DRAFT = "draft"


class CandidateSource(StrEnum):
    VISUAL_SIMILARITY = "visual_similarity"
    TEXT_SIMILARITY = "text_similarity"
    RULE_MATCH = "rule_match"
    ARCHITECT_SELECTION = "architect_selection"
    USER_SEARCH = "user_search"
    SUPPLIER_PROMOTION = "supplier_promotion"
    CHANNEL3_SEARCH = "channel3_search"


class CandidateStatus(StrEnum):
    DRAFT = "draft"
    SHORTLISTED = "shortlisted"
    PREVIEW_GENERATED = "preview_generated"
    REJECTED = "rejected"
    SELECTED = "selected"
    SUPERSEDED = "superseded"


class ScoreType(StrEnum):
    VISUAL_SIMILARITY = "visual_similarity"
    STYLE_FIT = "style_fit"
    DIMENSIONAL_FIT = "dimensional_fit"
    MATERIAL_FIT = "material_fit"
    BUDGET_FIT = "budget_fit"
    STOCK_SCORE = "stock_score"
    LEAD_TIME_SCORE = "lead_time_score"
    OVERALL_RERANKER = "overall_reranker"


class SubstitutionPreviewStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"


class ReviewDecisionType(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_EDIT = "needs_edit"


class SelectionStatus(StrEnum):
    DRAFT = "draft"
    CLIENT_SELECTED = "client_selected"
    ARCHITECT_APPROVED = "architect_approved"
    PROCUREMENT_APPROVED = "procurement_approved"
    ORDERED = "ordered"
    INSTALLED = "installed"


class ApprovalType(StrEnum):
    CLIENT_DESIGN = "client_design_approval"
    ARCHITECT_DESIGN = "architect_design_approval"
    TECHNICAL_REVIEW = "technical_review"
    PROCUREMENT = "procurement_approval"
    COMMERCIAL = "commercial_approval"
    REGION_GEOMETRY = "region_geometry_confirmation"


class ProcurementScheduleStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class ProcurementItemStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ORDERED = "ordered"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class SubstitutionPolicy(StrEnum):
    NO_SUBSTITUTION = "no_substitution"
    ARCHITECT_APPROVAL = "architect_approval_required"
    CLIENT_APPROVAL = "client_approval_required"
    EQUIVALENT_ALLOWED = "equivalent_allowed"


class IntegrationExportType(StrEnum):
    SCOPE_CSV = "scope_csv"
    SCOPE_JSON = "scope_json"
    QUOTE_LINES = "quote_lines"
    PROCUREMENT_CSV = "procurement_csv"
    PROCUREMENT_JSON = "procurement_json"


class IntegrationExportStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
