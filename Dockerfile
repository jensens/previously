# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# The dependencies exactly as `uv.lock` has them, then Previously itself in the
# version of the release, from PyPI, without resolving anything again. The
# image thus holds the package that is on PyPI and the versions the gates ran
# against ({ref}`delivery`).
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim@sha256:8e88a074b0969bdc461f681727238e109438d70771828909f9ef19cfcc96c43a

ARG PREVIOUSLY_VERSION

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# `wheels` is a named build context: an empty directory in the release
# workflow, where the package comes from PyPI; a directory holding a locally
# built wheel otherwise. One file, two ways in.
RUN --mount=type=bind,from=wheels,target=/wheels \
    uv pip install --python /app/.venv/bin/python --no-deps --find-links /wheels \
    "previously==${PREVIOUSLY_VERSION}"

RUN groupadd --system --gid 1000 previously \
    && useradd --system --uid 1000 --gid 1000 --home-dir /app --no-create-home --shell /usr/sbin/nologin previously
USER previously

LABEL org.opencontainers.image.source="https://github.com/jensens/previously" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      org.opencontainers.image.version="${PREVIOUSLY_VERSION}"

ENTRYPOINT ["previously"]
CMD ["--help"]
