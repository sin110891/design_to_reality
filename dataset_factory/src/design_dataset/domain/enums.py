from enum import StrEnum


class ReviewStatus(StrEnum):
    INGESTED = "ingested"
    DRAFT = "draft"
    VALIDATION_FAILED = "validation_failed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class LabelRunStatus(StrEnum):
    REQUESTED = "requested"
    SUCCEEDED = "succeeded"
    VALIDATION_FAILED = "validation_failed"
    PROVIDER_FAILED = "provider_failed"
    SKIPPED_IDEMPOTENT = "skipped_idempotent"


class UsageRightsStatus(StrEnum):
    UNKNOWN = "unknown"
    INTERNAL_REFERENCE_ONLY = "internal_reference_only"
    LICENSED_FOR_ANALYSIS = "licensed_for_analysis"
    LICENSED_FOR_TRAINING = "licensed_for_training"
    STUDIO_OWNED = "studio_owned"
    PERMISSION_GRANTED = "permission_granted"
    RESTRICTED = "restricted"


class SourceType(StrEnum):
    LOCAL_FOLDER = "local_folder"
    STUDIO = "studio"
    LICENSED = "licensed"
    UNKNOWN = "unknown"


class ErrorCategory(StrEnum):
    PROVIDER_TRANSIENT = "provider_transient"
    PROVIDER_PERMANENT = "provider_permanent"
    VALIDATION = "validation"
    BUSINESS_RULE = "business_rule"
    CONFIG = "config"
    IO = "io"
