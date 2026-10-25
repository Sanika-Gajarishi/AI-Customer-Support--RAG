"""Create orders table for customer order lookup."""

from alembic import op
import sqlalchemy as sa


# Revision identifiers.
revision = "c4e8b6a1d203"
down_revision = "a03d24b7a964"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "order_number",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="processing",
            nullable=False,
        ),
        sa.Column(
            "carrier",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "tracking_number",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "estimated_delivery",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_orders_order_number",
        "orders",
        ["order_number"],
        unique=True,
    )

    op.create_index(
        "ix_orders_user_id",
        "orders",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_orders_status",
        "orders",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orders_status",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_user_id",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_order_number",
        table_name="orders",
    )

    op.drop_table("orders")