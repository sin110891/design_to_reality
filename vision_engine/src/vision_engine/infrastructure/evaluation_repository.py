from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from vision_engine.domain.enums import (
    BenchmarkArm,
    EvaluationArmStatus,
    EvaluationCaseStatus,
    EvaluationExportStatus,
    EvaluationExportType,
    EvaluationRunStatus,
    EvaluationSelectionMethod,
)
from vision_engine.domain.evaluation_models import (
    BlindExportCandidate,
    EvaluationCase,
    EvaluationCaseArm,
    EvaluationExport,
    EvaluationRun,
    EvaluationSelection,
)
from vision_engine.infrastructure.evaluation_schema import (
    BlindExportCandidateRow,
    EvaluationCaseArmRow,
    EvaluationCaseRow,
    EvaluationExportRow,
    EvaluationRunRow,
    EvaluationSelectionRow,
)
from vision_engine.infrastructure.sqlite_repository import new_id, utcnow


class EvaluationRepositoryMixin:
    """Persistence for controlled evaluation entities."""

    def save_evaluation_run(self, run: EvaluationRun) -> None:
        with self.session() as session:
            session.merge(
                EvaluationRunRow(
                    evaluation_run_id=run.evaluation_run_id,
                    spec_sha256=run.spec_sha256,
                    spec_json=json.dumps(run.spec_json, sort_keys=True),
                    requested_repetitions=run.requested_repetitions,
                    status=run.status.value,
                    created_at=run.created_at,
                    completed_at=run.completed_at,
                )
            )

    def get_evaluation_run(self, evaluation_run_id: str) -> EvaluationRun | None:
        with self.session() as session:
            row = session.get(EvaluationRunRow, evaluation_run_id)
            return self._to_evaluation_run(row) if row else None

    def update_evaluation_run_status(
        self,
        evaluation_run_id: str,
        status: EvaluationRunStatus,
        *,
        completed_at: datetime | None = None,
    ) -> None:
        with self.session() as session:
            row = session.get(EvaluationRunRow, evaluation_run_id)
            if row is None:
                return
            row.status = status.value
            if completed_at is not None:
                row.completed_at = completed_at

    def save_evaluation_case(self, case: EvaluationCase) -> None:
        with self.session() as session:
            session.merge(
                EvaluationCaseRow(
                    evaluation_case_id=case.evaluation_case_id,
                    evaluation_run_id=case.evaluation_run_id,
                    case_input_sha256=case.case_input_sha256,
                    replicate_index=case.replicate_index,
                    public_case_id=case.public_case_id,
                    input_spec_json=json.dumps(case.input_spec_json, sort_keys=True),
                    status=case.status.value,
                    created_at=case.created_at,
                )
            )

    def list_evaluation_cases(self, evaluation_run_id: str) -> list[EvaluationCase]:
        with self.session() as session:
            rows = session.scalars(
                select(EvaluationCaseRow)
                .where(EvaluationCaseRow.evaluation_run_id == evaluation_run_id)
                .order_by(EvaluationCaseRow.public_case_id)
            ).all()
            return [self._to_evaluation_case(row) for row in rows]

    def get_evaluation_case(self, evaluation_case_id: str) -> EvaluationCase | None:
        with self.session() as session:
            row = session.get(EvaluationCaseRow, evaluation_case_id)
            return self._to_evaluation_case(row) if row else None

    def update_evaluation_case_status(
        self, evaluation_case_id: str, status: EvaluationCaseStatus
    ) -> None:
        with self.session() as session:
            row = session.get(EvaluationCaseRow, evaluation_case_id)
            if row is None:
                return
            row.status = status.value

    def save_evaluation_case_arm(self, arm: EvaluationCaseArm) -> None:
        with self.session() as session:
            session.merge(
                EvaluationCaseArmRow(
                    evaluation_case_arm_id=arm.evaluation_case_arm_id,
                    evaluation_case_id=arm.evaluation_case_id,
                    arm=arm.arm.value,
                    project_id=arm.project_id,
                    generation_run_id=arm.generation_run_id,
                    status=arm.status.value,
                    error_message=arm.error_message,
                    started_at=arm.started_at,
                    completed_at=arm.completed_at,
                )
            )

    def list_evaluation_case_arms(self, evaluation_case_id: str) -> list[EvaluationCaseArm]:
        with self.session() as session:
            rows = session.scalars(
                select(EvaluationCaseArmRow)
                .where(EvaluationCaseArmRow.evaluation_case_id == evaluation_case_id)
                .order_by(EvaluationCaseArmRow.arm)
            ).all()
            return [self._to_evaluation_case_arm(row) for row in rows]

    def list_evaluation_case_arms_for_run(
        self, evaluation_run_id: str
    ) -> list[EvaluationCaseArm]:
        with self.session() as session:
            rows = session.scalars(
                select(EvaluationCaseArmRow)
                .join(
                    EvaluationCaseRow,
                    EvaluationCaseRow.evaluation_case_id
                    == EvaluationCaseArmRow.evaluation_case_id,
                )
                .where(EvaluationCaseRow.evaluation_run_id == evaluation_run_id)
            ).all()
            return [self._to_evaluation_case_arm(row) for row in rows]

    def save_evaluation_export(self, export: EvaluationExport) -> None:
        with self.session() as session:
            session.merge(
                EvaluationExportRow(
                    evaluation_export_id=export.evaluation_export_id,
                    evaluation_run_id=export.evaluation_run_id,
                    export_type=export.export_type.value,
                    output_directory=export.output_directory,
                    manifest_sha256=export.manifest_sha256,
                    status=export.status.value,
                    created_at=export.created_at,
                )
            )

    def get_evaluation_export(self, evaluation_export_id: str) -> EvaluationExport | None:
        with self.session() as session:
            row = session.get(EvaluationExportRow, evaluation_export_id)
            return self._to_evaluation_export(row) if row else None

    def list_evaluation_exports(
        self,
        evaluation_run_id: str,
        *,
        export_type: EvaluationExportType | None = None,
    ) -> list[EvaluationExport]:
        with self.session() as session:
            stmt = select(EvaluationExportRow).where(
                EvaluationExportRow.evaluation_run_id == evaluation_run_id
            )
            if export_type is not None:
                stmt = stmt.where(EvaluationExportRow.export_type == export_type.value)
            rows = session.scalars(stmt.order_by(EvaluationExportRow.created_at.desc())).all()
            return [self._to_evaluation_export(row) for row in rows]

    def save_blind_export_candidate(self, candidate: BlindExportCandidate) -> None:
        with self.session() as session:
            session.merge(
                BlindExportCandidateRow(
                    blind_candidate_id=candidate.blind_candidate_id,
                    evaluation_export_id=candidate.evaluation_export_id,
                    evaluation_case_id=candidate.evaluation_case_id,
                    public_case_id=candidate.public_case_id,
                    variant_id=candidate.variant_id,
                    arm=candidate.arm.value,
                    image_sha256=candidate.image_sha256,
                    display_order=candidate.display_order,
                )
            )

    def list_blind_export_candidates(
        self, evaluation_export_id: str
    ) -> list[BlindExportCandidate]:
        with self.session() as session:
            rows = session.scalars(
                select(BlindExportCandidateRow)
                .where(BlindExportCandidateRow.evaluation_export_id == evaluation_export_id)
                .order_by(
                    BlindExportCandidateRow.public_case_id,
                    BlindExportCandidateRow.display_order,
                )
            ).all()
            return [self._to_blind_export_candidate(row) for row in rows]

    def get_blind_export_candidate(
        self, blind_candidate_id: str
    ) -> BlindExportCandidate | None:
        with self.session() as session:
            row = session.get(BlindExportCandidateRow, blind_candidate_id)
            return self._to_blind_export_candidate(row) if row else None

    def save_evaluation_selection(self, selection: EvaluationSelection) -> None:
        with self.session() as session:
            existing = session.scalars(
                select(EvaluationSelectionRow).where(
                    EvaluationSelectionRow.evaluation_export_id
                    == selection.evaluation_export_id,
                    EvaluationSelectionRow.evaluation_case_id
                    == selection.evaluation_case_id,
                    EvaluationSelectionRow.evaluator_id == selection.evaluator_id,
                )
            ).first()
            if existing is None:
                session.add(
                    EvaluationSelectionRow(
                        selection_id=selection.selection_id,
                        evaluation_export_id=selection.evaluation_export_id,
                        evaluation_case_id=selection.evaluation_case_id,
                        public_case_id=selection.public_case_id,
                        evaluator_id=selection.evaluator_id,
                        winner_candidate_id=selection.winner_candidate_id,
                        winner_arm=selection.winner_arm.value if selection.winner_arm else None,
                        selection_method=selection.selection_method.value,
                        submitted_at=selection.submitted_at,
                    )
                )
                return

            existing.winner_candidate_id = selection.winner_candidate_id
            existing.winner_arm = selection.winner_arm.value if selection.winner_arm else None
            existing.selection_method = selection.selection_method.value
            existing.submitted_at = selection.submitted_at

    def list_evaluation_selections(
        self, evaluation_export_id: str
    ) -> list[EvaluationSelection]:
        with self.session() as session:
            rows = session.scalars(
                select(EvaluationSelectionRow)
                .where(EvaluationSelectionRow.evaluation_export_id == evaluation_export_id)
                .order_by(EvaluationSelectionRow.public_case_id)
            ).all()
            return [self._to_evaluation_selection(row) for row in rows]

    @staticmethod
    def _to_evaluation_run(row: EvaluationRunRow) -> EvaluationRun:
        return EvaluationRun(
            evaluation_run_id=row.evaluation_run_id,
            spec_sha256=row.spec_sha256,
            spec_json=json.loads(row.spec_json),
            requested_repetitions=row.requested_repetitions,
            status=EvaluationRunStatus(row.status),
            created_at=row.created_at,
            completed_at=row.completed_at,
        )

    @staticmethod
    def _to_evaluation_case(row: EvaluationCaseRow) -> EvaluationCase:
        return EvaluationCase(
            evaluation_case_id=row.evaluation_case_id,
            evaluation_run_id=row.evaluation_run_id,
            case_input_sha256=row.case_input_sha256,
            replicate_index=row.replicate_index,
            public_case_id=row.public_case_id,
            input_spec_json=json.loads(row.input_spec_json),
            status=EvaluationCaseStatus(row.status),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_evaluation_case_arm(row: EvaluationCaseArmRow) -> EvaluationCaseArm:
        return EvaluationCaseArm(
            evaluation_case_arm_id=row.evaluation_case_arm_id,
            evaluation_case_id=row.evaluation_case_id,
            arm=BenchmarkArm(row.arm),
            project_id=row.project_id,
            generation_run_id=row.generation_run_id,
            status=EvaluationArmStatus(row.status),
            error_message=row.error_message,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    @staticmethod
    def _to_evaluation_export(row: EvaluationExportRow) -> EvaluationExport:
        return EvaluationExport(
            evaluation_export_id=row.evaluation_export_id,
            evaluation_run_id=row.evaluation_run_id,
            export_type=EvaluationExportType(row.export_type),
            output_directory=row.output_directory,
            manifest_sha256=row.manifest_sha256,
            status=EvaluationExportStatus(row.status),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_blind_export_candidate(row: BlindExportCandidateRow) -> BlindExportCandidate:
        return BlindExportCandidate(
            blind_candidate_id=row.blind_candidate_id,
            evaluation_export_id=row.evaluation_export_id,
            evaluation_case_id=row.evaluation_case_id,
            public_case_id=row.public_case_id,
            variant_id=row.variant_id,
            arm=BenchmarkArm(row.arm),
            image_sha256=row.image_sha256,
            display_order=row.display_order,
        )

    @staticmethod
    def _to_evaluation_selection(row: EvaluationSelectionRow) -> EvaluationSelection:
        return EvaluationSelection(
            selection_id=row.selection_id,
            evaluation_export_id=row.evaluation_export_id,
            evaluation_case_id=row.evaluation_case_id,
            public_case_id=row.public_case_id,
            evaluator_id=row.evaluator_id,
            winner_candidate_id=row.winner_candidate_id,
            winner_arm=BenchmarkArm(row.winner_arm) if row.winner_arm else None,
            selection_method=EvaluationSelectionMethod(row.selection_method),
            submitted_at=row.submitted_at,
        )
