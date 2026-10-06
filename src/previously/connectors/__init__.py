# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The connectors: each reads one kind of source and hands its bytes to
`core` through the protocol in `contract.connector`.

A layer of its own between `cli` and `core`, because a connector speaks a
foreign protocol and `core` must not: `.importlinter` keeps `imaplib` in
`connectors.imap` by name.
"""
