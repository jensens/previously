# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sphinx configuration for the Previously documentation."""

project = "Previously"
author = "Jens W. Klein"
copyright = "2026, Jens W. Klein"  # noqa: A001 — Sphinx requires this exact name

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",
]

myst_enable_extensions = [
    "attrs_block",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "linkify",
    "strikethrough",
    "substitution",
]

# The design records under docs/superpowers/ are frozen German documents and
# the plans are working notes. They stay in the repository for provenance but
# they are not part of the published documentation: without this exclusion
# Sphinx pulls 2000 lines of German into the build, warns about every file
# missing from a toctree, and publishes the plans (review finding 3 of the
# plan's Review Focus).
exclude_patterns = [
    "_build",
    "superpowers/**",
]

html_theme = "sphinx_book_theme"
html_title = "Previously"

html_theme_options = {
    "repository_url": "https://github.com/jensens/previously",
    "repository_branch": "main",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "navigation_with_keys": True,
}

# External hosts that rate-limit or block HEAD requests. Listed here rather
# than dropped from linkcheck entirely: the skill forbids disabling linkcheck
# to hide broken links, and these are not broken — they answer a browser and
# refuse a crawler.
linkcheck_ignore = [
    r"https://github\.com/.*/(issues|pull)/\d+",
]
linkcheck_timeout = 20
