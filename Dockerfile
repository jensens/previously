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
# Compiled at build time, by both installs below: the venv belongs to root, so
# the user the image runs as cannot write a `__pycache__`, and without this
# every command compiled its imports again at every start. Measured on
# 2026-10-05, the median of three runs inside the container: `previously
# --help` took 1.70 s without it and 0.83 s with it, for an image of 332 MB
# instead of 313 MB.
ENV UV_COMPILE_BYTECODE=1

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
# By number, not by name: the kubelet cannot tell whether a name is root, and
# refuses to start a pod with `runAsNonRoot` and no `runAsUser` on an image
# whose user is a name. The name above stays, so `id` still says `previously`.
USER 1000:1000

# The commit and the moment of the release, passed in by the release
# workflow. Without them, the two labels stay empty rather than keep the
# values of the base image, which name a commit and a day of `uv`.
ARG PREVIOUSLY_REVISION=""
ARG PREVIOUSLY_CREATED=""

# Every label the base image sets is set here as well, so that none of them
# describes `uv`.
LABEL org.opencontainers.image.title="previously" \
      org.opencontainers.image.description="An append-only knowledge store for project histories" \
      org.opencontainers.image.url="https://github.com/jensens/previously" \
      org.opencontainers.image.source="https://github.com/jensens/previously" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      org.opencontainers.image.version="${PREVIOUSLY_VERSION}" \
      org.opencontainers.image.revision="${PREVIOUSLY_REVISION}" \
      org.opencontainers.image.created="${PREVIOUSLY_CREATED}"

ENTRYPOINT ["previously"]
CMD ["--help"]
