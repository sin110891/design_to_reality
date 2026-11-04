from enum import StrEnum


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProjectStatus(StrEnum):
    CREATED = "created"
    ANALYSED = "analysed"
    RETRIEVED = "retrieved"
    CONCEPT_READY = "concept_ready"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    FAILED = "failed"


class GenerationMode(StrEnum):
    BASELINE = "baseline"
    CURATED = "curated"


class VariantKind(StrEnum):
    CLOSEST = "closest_to_references"
    CONSERVATIVE = "conservative"
    EXPRESSIVE = "expressive"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_EDIT = "needs_edit"
    NOT_ASSESSABLE = "not_assessable"


class VariantReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    NEEDS_EDIT = "needs_edit"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class GenerationReviewSetStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    FINALISED = "finalised"
    SUPERSEDED = "superseded"


class BuildabilityAssessment(StrEnum):
    ASSESSABLE = "assessable"
    NOT_ASSESSABLE_FROM_VISUAL = "not_assessable_from_visual"
    REQUIRES_SITE_VERIFICATION = "requires_site_verification"


class RightsStatus(StrEnum):
    UNKNOWN = "unknown"
    USER_OWNED = "user_owned"
    LICENSED_FOR_INTERNAL_REVIEW = "licensed_for_internal_review"
    LICENSED_FOR_EVALUATION = "licensed_for_evaluation"
    LICENSED_FOR_MODEL_TRAINING = "licensed_for_model_training"
    RESTRICTED = "restricted"


class RetentionConsentStatus(StrEnum):
    PENDING = "pending"
    INTERNAL_REVIEW_ONLY = "internal_review_only"
    EVALUATION_ALLOWED = "evaluation_allowed"
    MODEL_TRAINING_ALLOWED = "model_training_allowed"
    WITHDRAWN = "withdrawn"
    NOT_REQUIRED = "not_required"


class ApprovedConceptExportStatus(StrEnum):
    PENDING_VALIDATION = "pending_validation"
    APPROVED_FOR_EVALUATION = "approved_for_evaluation"
    APPROVED_FOR_TRAINING = "approved_for_training"
    EXPORTED = "exported"
    WITHDRAWN = "withdrawn"
    BLOCKED_BY_RIGHTS = "blocked_by_rights"


class BenchmarkArm(StrEnum):
    BASELINE = "baseline"
    CURATED = "curated"
    USER_INSPIRATION = "user_inspiration"
    HUMAN_REFERENCE = "human_reference"


class LabelPolarity(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class FailureTag(StrEnum):
    LIGHTING_PROBLEM = "lighting_problem"
    SCALE_PROBLEM = "scale_problem"
    MATERIAL_CONFLICT = "material_conflict"
    GEOMETRY_FAILURE = "geometry_failure"
    TASTE_ERROR = "taste_error"
    GENERIC_AI_ARTIFACT = "generic_ai_artifact"
    STRUCTURAL_VIOLATION = "structural_violation"
    IMPRACTICAL_DETAIL = "impractical_detail"
    REFERENCE_MISMATCH = "reference_mismatch"
    OTHER = "other"


class BudgetBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    MEDIUM_HIGH = "medium_high"
    HIGH = "high"


class RoomType(StrEnum):
    LIVING_ROOM = "living_room"
    KITCHEN = "kitchen"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    DINING_ROOM = "dining_room"
    HALLWAY = "hallway"
    STUDY = "study"
    OUTDOOR = "outdoor"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class DatasetSnapshotStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    SEALED = "sealed"
    DEPRECATED = "deprecated"


class AnnotationRevisionStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class EmbeddingJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EmbeddingModality(StrEnum):
    IMAGE = "image"
    TEXT = "text"
    JOINT = "joint"


class VectorIndexStatus(StrEnum):
    BUILDING = "building"
    VALIDATION_FAILED = "validation_failed"
    VALIDATED = "validated"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class RetrievalExperimentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class RetrievalScoreStage(StrEnum):
    VECTOR_IMAGE = "vector_image"
    VECTOR_TEXT = "vector_text"
    LEXICAL = "lexical"
    METADATA = "metadata"
    QUALITY_PRIOR = "quality_prior"
    FUSION = "fusion"
    MULTIMODAL_RERANKER = "multimodal_reranker"
    PREFERENCE_RERANKER = "preference_reranker"
    DIVERSITY = "diversity"


class RerankerModelStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class RetrievalEvaluationSetStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class RetrievalEvaluationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRunStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class EvaluationCaseStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class EvaluationArmStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class EvaluationExportType(StrEnum):
    FULL = "full"
    BLIND = "blind"


class EvaluationExportStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationSelectionMethod(StrEnum):
    CSV = "csv"
    IMAGE_SHA256 = "image_sha256"
