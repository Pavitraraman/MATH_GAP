"""initial schema

Revision ID: 20260519_0001
Revises:
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260519_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_assessments_student_id", "assessments", ["student_id"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_prompt_versions_name", "prompt_versions", ["name"])
    op.create_index("ix_prompt_versions_version", "prompt_versions", ["version"])

    op.create_table(
        "llm_call_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "topic_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )
    op.create_index("ix_topic_scores_assessment_id", "topic_scores", ["assessment_id"])
    op.create_index("ix_topic_scores_topic", "topic_scores", ["topic"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("weak_topics_json", sa.JSON(), nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recommendations_assessment_id", "recommendations", ["assessment_id"])
    op.create_index("ix_recommendations_student_id", "recommendations", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendations_student_id", table_name="recommendations")
    op.drop_index("ix_recommendations_assessment_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_topic_scores_topic", table_name="topic_scores")
    op.drop_index("ix_topic_scores_assessment_id", table_name="topic_scores")
    op.drop_table("topic_scores")
    op.drop_table("llm_call_logs")
    op.drop_index("ix_prompt_versions_version", table_name="prompt_versions")
    op.drop_index("ix_prompt_versions_name", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_index("ix_assessments_student_id", table_name="assessments")
    op.drop_table("assessments")
