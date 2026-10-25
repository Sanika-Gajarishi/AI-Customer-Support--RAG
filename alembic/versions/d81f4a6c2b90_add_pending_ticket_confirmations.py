"""Add persistent, expiring support-ticket confirmations."""

from alembic import op
import sqlalchemy as sa


# Revision identifiers.
revision = "d81f4a6c2b90"
down_revision = "c4e8b6a1d203"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_ticket_confirmations",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "confirmation_code",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "conversation_session_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "subject",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.String(length=20),
            server_default="medium",
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "consumed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["support_tickets.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "ticket_id",
            name="uq_pending_ticket_confirmations_ticket_id",
        ),
    )

    op.create_index(
        "ix_pending_ticket_confirmations_confirmation_code",
        "pending_ticket_confirmations",
        ["confirmation_code"],
        unique=True,
    )

    op.create_index(
        "ix_pending_ticket_confirmations_user_id",
        "pending_ticket_confirmations",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_pending_ticket_confirmations_conversation_session_id",
        "pending_ticket_confirmations",
        ["conversation_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pending_ticket_confirmations_conversation_session_id",
        table_name="pending_ticket_confirmations",
    )

    op.drop_index(
        "ix_pending_ticket_confirmations_user_id",
        table_name="pending_ticket_confirmations",
    )

    op.drop_index(
        "ix_pending_ticket_confirmations_confirmation_code",
        table_name="pending_ticket_confirmations",
    )

    op.drop_table("pending_ticket_confirmations")