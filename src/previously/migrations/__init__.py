# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The Alembic migrations that create and evolve the database schema.

They live inside the package so that an installed wheel carries them, and
Alembic finds them through `script_location = previously:migrations` in
`alembic.ini`, a package resource rather than a path beside a checkout.
"""
