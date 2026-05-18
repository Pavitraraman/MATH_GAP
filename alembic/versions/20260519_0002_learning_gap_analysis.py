"""learning gap analysis storage

Revision ID: 20260519_0002
Revises: 20260519_0001
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260519_0002"
down_revision = "20260519_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_gap_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("prompt_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("input_summary_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_learning_gap_analyses_student_id", "learning_gap_analyses", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_gap_analyses_student_id", table_name="learning_gap_analyses")
    op.drop_table("learning_gap_analyses")
