"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)

    op.create_table(
        "farms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("village", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=False),
        sa.Column("area", sa.Float(), nullable=True),
        sa.Column("area_unit", sa.String(length=20), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_farms_id"), "farms", ["id"], unique=False)
    op.create_index(op.f("ix_farms_user_id"), "farms", ["user_id"], unique=False)

    op.create_table(
        "crops",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("farm_id", sa.Integer(), nullable=False),
        sa.Column("crop_type", sa.String(length=120), nullable=False),
        sa.Column("crop_variety", sa.String(length=120), nullable=True),
        sa.Column("sowing_date", sa.Date(), nullable=True),
        sa.Column("growth_stage", sa.String(length=80), nullable=True),
        sa.Column("irrigation_type", sa.String(length=80), nullable=True),
        sa.Column("field_size", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crops_crop_type"), "crops", ["crop_type"], unique=False)
    op.create_index(op.f("ix_crops_farm_id"), "crops", ["farm_id"], unique=False)
    op.create_index(op.f("ix_crops_id"), "crops", ["id"], unique=False)

    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("farm_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_images_farm_id"), "images", ["farm_id"], unique=False)
    op.create_index(op.f("ix_images_id"), "images", ["id"], unique=False)
    op.create_index(op.f("ix_images_user_id"), "images", ["user_id"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("farm_id", sa.Integer(), nullable=True),
        sa.Column("crop_id", sa.Integer(), nullable=True),
        sa.Column("input_type", sa.String(length=30), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("context_snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_crop_id"), "conversations", ["crop_id"], unique=False)
    op.create_index(op.f("ix_conversations_farm_id"), "conversations", ["farm_id"], unique=False)
    op.create_index(op.f("ix_conversations_id"), "conversations", ["id"], unique=False)
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("farm_id", sa.Integer(), nullable=True),
        sa.Column("crop_id", sa.Integer(), nullable=True),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column("crop_name", sa.String(length=120), nullable=False),
        sa.Column("crop_confidence", sa.Float(), nullable=False),
        sa.Column("disease_name", sa.String(length=160), nullable=False),
        sa.Column("disease_confidence", sa.Float(), nullable=False),
        sa.Column("severity_label", sa.String(length=80), nullable=False),
        sa.Column("severity_score", sa.Float(), nullable=False),
        sa.Column("xai_summary", sa.Text(), nullable=False),
        sa.Column("model_trace", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_crop_id"), "predictions", ["crop_id"], unique=False)
    op.create_index(op.f("ix_predictions_farm_id"), "predictions", ["farm_id"], unique=False)
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)
    op.create_index(op.f("ix_predictions_image_id"), "predictions", ["image_id"], unique=False)
    op.create_index(op.f("ix_predictions_user_id"), "predictions", ["user_id"], unique=False)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("farm_id", sa.Integer(), nullable=True),
        sa.Column("crop_id", sa.Integer(), nullable=True),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("urgency", sa.String(length=40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("safety_notes", sa.Text(), nullable=True),
        sa.Column("weather_constraints", sa.Text(), nullable=True),
        sa.Column("structured_payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendations_crop_id"), "recommendations", ["crop_id"], unique=False)
    op.create_index(op.f("ix_recommendations_farm_id"), "recommendations", ["farm_id"], unique=False)
    op.create_index(op.f("ix_recommendations_id"), "recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_recommendations_prediction_id"), "recommendations", ["prediction_id"], unique=False)
    op.create_index(op.f("ix_recommendations_user_id"), "recommendations", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("predictions")
    op.drop_table("conversations")
    op.drop_table("images")
    op.drop_table("crops")
    op.drop_table("farms")
    op.drop_table("users")
