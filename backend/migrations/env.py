from alembic import context
from sqlalchemy import create_engine

from smartdesk.config import get_settings
from smartdesk.infrastructure.postgres.database_models import Base

engine = create_engine(get_settings().database_url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
