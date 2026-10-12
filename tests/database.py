"""The PostgreSQL every test runs against, configured in one place.

A test database holds nothing worth keeping, so the server is told not to
wait for the disk: `fsync=off` and `synchronous_commit=off` drop the flush at
every commit, and `full_page_writes=off` the page images a crash would need.
None of the three changes what a query returns or which lock it takes; they
change only what survives a crash of the container, and a crashed container is
thrown away with its data. The suite commits often — every test empties the
tables and every write path takes its own transaction — so the flush was a
large share of its run time.
"""

from testcontainers.community.postgres import PostgresContainer


IMAGE = "postgres:18"
SETTINGS = ("fsync=off", "synchronous_commit=off", "full_page_writes=off")


def postgres() -> PostgresContainer:
    """A PostgreSQL container with the settings above, not started yet."""
    command = " ".join(["postgres", *(f"-c {setting}" for setting in SETTINGS)])
    return PostgresContainer(IMAGE, driver="psycopg").with_command(command)
