"""Initial application tables, separate from LangGraph checkpoints."""

from alembic import op

from smartdesk.infrastructure.postgres.database_models import Base

revision = "0001"
down_revision = None


def upgrade():
    Base.metadata.create_all(op.get_bind())


def downgrade():
    Base.metadata.drop_all(op.get_bind())
