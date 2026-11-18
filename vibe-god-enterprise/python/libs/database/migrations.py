"""
Database Migrations with Alembic
"""
import os
import logging
from typing import Optional, List
from pathlib import Path
from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

from .core import Database, DatabaseConfig

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages database migrations using Alembic.
    """

    def __init__(
        self,
        database: Database,
        migrations_dir: Optional[str] = None,
    ):
        self.database = database
        self.migrations_dir = migrations_dir or "migrations"
        self._alembic_config: Optional[AlembicConfig] = None

    def _get_alembic_config(self) -> AlembicConfig:
        """Get or create Alembic configuration."""
        if self._alembic_config is None:
            # Find migrations directory
            migrations_path = Path(self.migrations_dir)
            if not migrations_path.is_absolute():
                # Look relative to current file
                base_dir = Path(__file__).parent.parent.parent.parent
                migrations_path = base_dir / self.migrations_dir

            # Create directory if not exists
            migrations_path.mkdir(parents=True, exist_ok=True)

            # Create alembic.ini if not exists
            ini_path = migrations_path / "alembic.ini"
            if not ini_path.exists():
                self._create_alembic_ini(ini_path, migrations_path)

            self._alembic_config = AlembicConfig(str(ini_path))
            self._alembic_config.set_main_option("script_location", str(migrations_path))
            self._alembic_config.set_main_option(
                "sqlalchemy.url",
                self.database.config.url.replace("+asyncpg", ""),  # Use sync URL for alembic
            )

        return self._alembic_config

    def _create_alembic_ini(self, ini_path: Path, migrations_path: Path) -> None:
        """Create default alembic.ini."""
        ini_content = f"""# Alembic Configuration
[alembic]
script_location = {migrations_path}
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
# hooks = black
# black.type = console_scripts
# black.entrypoint = black

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
        ini_path.write_text(ini_content)

        # Create env.py
        env_path = migrations_path / "env.py"
        env_content = '''"""Alembic environment configuration."""
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from python.libs.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with async engine."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url").replace("postgresql://", "postgresql+asyncpg://"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    import asyncio
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        env_path.write_text(env_content)

        # Create versions directory
        versions_path = migrations_path / "versions"
        versions_path.mkdir(exist_ok=True)

        logger.info(f"Created Alembic configuration at {migrations_path}")

    async def init_migrations(self) -> None:
        """Initialize migration environment."""
        config = self._get_alembic_config()

        # Create initial migration if no versions exist
        versions_dir = Path(config.get_main_option("script_location")) / "versions"
        if not any(versions_dir.iterdir()):
            await self.create_migration("initial", "Initial migration")

    async def create_migration(self, message: str, head: str = "head") -> str:
        """
        Create a new migration.

        Args:
            message: Migration message
            head: Revision to base on

        Returns:
            Migration revision identifier
        """
        config = self._get_alembic_config()

        # Run in thread pool since alembic is synchronous
        import asyncio
        loop = asyncio.get_event_loop()

        def _create():
            return command.revision(
                config,
                message=message,
                autogenerate=True,
                head=head,
            )

        await loop.run_in_executor(None, _create)

        # Get the latest revision
        script = ScriptDirectory.from_config(config)
        revisions = list(script.walk_revisions("head", 1))
        if revisions:
            return revisions[0].revision
        return ""

    async def upgrade(self, revision: str = "head") -> None:
        """
        Upgrade database to revision.

        Args:
            revision: Target revision (default: head)
        """
        config = self._get_alembic_config()

        import asyncio
        loop = asyncio.get_event_loop()

        def _upgrade():
            command.upgrade(config, revision)

        await loop.run_in_executor(None, _upgrade)
        logger.info(f"Upgraded database to {revision}")

    async def downgrade(self, revision: str = "-1") -> None:
        """
        Downgrade database to revision.

        Args:
            revision: Target revision (default: -1 for one step)
        """
        config = self._get_alembic_config()

        import asyncio
        loop = asyncio.get_event_loop()

        def _downgrade():
            command.downgrade(config, revision)

        await loop.run_in_executor(None, _downgrade)
        logger.info(f"Downgraded database to {revision}")

    async def current_revision(self) -> Optional[str]:
        """Get current database revision."""
        if not self.database._engine:
            return None

        async with self.database._engine.connect() as conn:
            context = MigrationContext.configure(conn.sync_connection)
            return context.get_current_revision()

    async def history(self, verbose: bool = False) -> List[dict]:
        """Get migration history."""
        config = self._get_alembic_config()
        script = ScriptDirectory.from_config(config)

        revisions = []
        for rev in script.walk_revisions():
            revisions.append({
                "revision": rev.revision,
                "down_revision": rev.down_revision,
                "message": rev.doc,
                "branch_labels": rev.branch_labels,
            })
        return revisions

    async def show_current(self) -> dict:
        """Show current migration status."""
        current = await self.current_revision()
        history = await self.history()

        return {
            "current": current,
            "pending": [
                r for r in history
                if r["revision"] != current and
                (current is None or self._is_ancestor(r["revision"], current, history))
            ],
            "applied": [
                r for r in history
                if current is not None and self._is_ancestor(r["revision"], current, history) or r["revision"] == current
            ],
        }

    def _is_ancestor(self, revision: str, target: str, history: List[dict]) -> bool:
        """Check if revision is ancestor of target."""
        rev_map = {r["revision"]: r for r in history}
        current = target
        while current and current in rev_map:
            if current == revision:
                return True
            current = rev_map[current].get("down_revision")
        return False

    async def stamp(self, revision: str = "head") -> None:
        """Stamp database with revision without running migrations."""
        config = self._get_alembic_config()

        import asyncio
        loop = asyncio.get_event_loop()

        def _stamp():
            command.stamp(config, revision)

        await loop.run_in_executor(None, _stamp)
        logger.info(f"Stamped database with {revision}")


async def run_migrations(
    database: Database,
    direction: str = "upgrade",
    revision: str = "head",
    migrations_dir: Optional[str] = None,
) -> None:
    """
    Convenience function to run migrations.

    Args:
        database: Database instance
        direction: "upgrade" or "downgrade"
        revision: Target revision
        migrations_dir: Migrations directory
    """
    manager = MigrationManager(database, migrations_dir)
    await manager.init_migrations()

    if direction == "upgrade":
        await manager.upgrade(revision)
    elif direction == "downgrade":
        await manager.downgrade(revision)
    else:
        raise ValueError(f"Invalid direction: {direction}")


# CLI commands (for use with click/typer)
def create_migration_cli(message: str, migrations_dir: str = "migrations") -> str:
    """CLI command to create migration."""
    import asyncio
    from .core import init_database

    async def _create():
        db = await init_database()
        manager = MigrationManager(db, migrations_dir)
        await manager.init_migrations()
        return await manager.create_migration(message)

    return asyncio.run(_create())


def upgrade_cli(revision: str = "head", migrations_dir: str = "migrations") -> None:
    """CLI command to upgrade."""
    import asyncio
    from .core import init_database

    async def _upgrade():
        db = await init_database()
        manager = MigrationManager(db, migrations_dir)
        await manager.upgrade(revision)

    asyncio.run(_upgrade())


def downgrade_cli(revision: str = "-1", migrations_dir: str = "migrations") -> None:
    """CLI command to downgrade."""
    import asyncio
    from .core import init_database

    async def _downgrade():
        db = await init_database()
        manager = MigrationManager(db, migrations_dir)
        await manager.downgrade(revision)

    asyncio.run(_downgrade())