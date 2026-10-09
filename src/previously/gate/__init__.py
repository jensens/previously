# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The gate: where a model call is decided, made and recorded.

The one package that imports vendor SDKs, and `.importlinter` holds it to
that: `gate.adapters.anthropic` may import `anthropic`,
`gate.adapters.openai_compatible` may import `openai`, and nothing else in
the package may import either.
"""
