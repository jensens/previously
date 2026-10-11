# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""No setting of Previously can be set by Kubernetes behind its back.

The kubelet gives every container one set of variables per Service in its
namespace, the Service's name upper-cased with `-` turned into `_` as the
prefix `X`. The Kubernetes documentation lists them under "Environment
variables" on the page "Service", with the example of `redis-primary`:

    X_SERVICE_HOST, X_SERVICE_PORT, X_PORT,
    X_PORT_<n>_<PROTO>, X_PORT_<n>_<PROTO>_PROTO,
    X_PORT_<n>_<PROTO>_PORT, X_PORT_<n>_<PROTO>_ADDR

and the kubelet's `FromServices` in `pkg/kubelet/envvars/envvars.go`, which
that page links to, adds `X_SERVICE_PORT_<NAME>` for every named port; both
read on 2026-10-11. `<n>` is the port's number and `<PROTO>` its protocol,
`TCP`, `UDP` or `SCTP`.

Docker's legacy links set the same names, and `X_NAME` and `X_ENV_<VARIABLE>`
beside them, which are held here as well.

A Service named `previously-mcp` therefore set `PREVIOUSLY_MCP_PORT` to
`tcp://<cluster IP>:8765` in every pod of its namespace, which until
2026-10-11 was the port `previously serve` read, and `serve` refused to start
in the tools pod (`docs/superpowers/handoffs/2026-10-11-kup6s-feedback-gate-and-mcp.md`).
A name of ours that Kubernetes can produce is our defect, not something the
environment has to switch off ({ref}`configuration-reference`).

The names are collected from the source and not listed here, so that a new
setting is held to this the day it is read.
"""

import ast
import pathlib
import pytest
import re


SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "previously"

# Everything after the prefix `X_`, which is a Service name and so can be any
# run of letters, digits and underscores.
SERVICE_LINK = re.compile(
    r"[A-Z][A-Z0-9_]*_"
    r"(?:SERVICE_HOST|SERVICE_PORT(?:_[A-Z0-9_]+)?"
    r"|PORT(?:_[0-9]+_(?:TCP|UDP|SCTP)(?:_(?:PROTO|PORT|ADDR))?)?)"
)
# Docker's legacy links, which Kubernetes copied, set the same names and two
# more forms beside them: `X_NAME`, and `X_ENV_<VARIABLE>` for every variable
# of the linked container.
DOCKER_LINK = re.compile(r"[A-Z][A-Z0-9_]*_(?:NAME|ENV_[A-Z0-9_]+)")
_NAME = re.compile(r"PREVIOUSLY_[A-Z0-9_]*[A-Z0-9]")


def _docstrings(tree: ast.Module) -> set[int]:
    """The ids of every string that stands alone as a statement: a docstring
    describes a setting and reads none."""
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }


def names_in_source() -> set[str]:
    """Every `PREVIOUSLY_…` name in a string of the source, docstrings left
    out: the names `os.environ` is asked for, the constants they are kept in,
    and the messages that name them.

    A name put together at run time, such as `f"PREVIOUSLY_{x}_PORT"`, is not
    found; no read in the source does that.
    """
    found: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skipped = _docstrings(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in skipped
            ):
                found.update(_NAME.findall(node.value))
    return found


def test_no_setting_has_a_name_that_kubernetes_gives_a_service() -> None:
    names = names_in_source()
    # The control that the collection reads what it should: settings read
    # through a literal, through `_setting`, and through constants of other
    # modules than `cli`.
    assert {
        "PREVIOUSLY_DSN",
        "PREVIOUSLY_BLOB_SECRET_KEY",
        "PREVIOUSLY_IMAP_ADDRESS",
        "PREVIOUSLY_MCP_ADDRESS",
        "PREVIOUSLY_MCP_CLIENT",
        "PREVIOUSLY_LOCAL_MODEL_URL",
    } <= names
    colliding = sorted(
        name for name in names if SERVICE_LINK.fullmatch(name) or DOCKER_LINK.fullmatch(name)
    )
    assert colliding == [], (
        f"{colliding}: a Service whose name upper-cases to the part before the "
        "suffix sets this variable in every pod of its namespace"
    )


@pytest.mark.parametrize(
    "name",
    [
        # The example of the Kubernetes documentation, whole.
        "REDIS_PRIMARY_SERVICE_HOST",
        "REDIS_PRIMARY_SERVICE_PORT",
        "REDIS_PRIMARY_PORT",
        "REDIS_PRIMARY_PORT_6379_TCP",
        "REDIS_PRIMARY_PORT_6379_TCP_PROTO",
        "REDIS_PRIMARY_PORT_6379_TCP_PORT",
        "REDIS_PRIMARY_PORT_6379_TCP_ADDR",
        # A named port, from the kubelet's source, and the other protocols.
        "REDIS_PRIMARY_SERVICE_PORT_METRICS",
        "PREVIOUSLY_SERVICE_PORT_HTTP_ALT",
        "DNS_PORT_53_UDP",
        "SIGNALING_PORT_2905_SCTP_ADDR",
        # The two names Previously read until 2026-10-11, and the ones a
        # Service `previously-imap` or `previously` would set.
        "PREVIOUSLY_MCP_PORT",
        "PREVIOUSLY_IMAP_PORT",
        "PREVIOUSLY_PORT",
        "PREVIOUSLY_SERVICE_HOST",
    ],
)
def test_the_pattern_matches_every_variable_of_a_service(name: str) -> None:
    assert SERVICE_LINK.fullmatch(name)


@pytest.mark.parametrize(
    "name",
    [
        "PREVIOUSLY_MCP_ADDRESS",
        "PREVIOUSLY_IMAP_ADDRESS",
        "PREVIOUSLY_MCP_HOST",
        "PREVIOUSLY_IMAP_HOST",
        "PREVIOUSLY_MCP_ALLOWED_HOSTS",
        "PREVIOUSLY_LOCAL_MODEL_URL",
        "PREVIOUSLY_PORTAL",
        "PREVIOUSLY_PORT_8765",
        "PREVIOUSLY_PORT_8765_TCP_HOST",
    ],
)
def test_the_pattern_leaves_every_other_name_alone(name: str) -> None:
    assert not SERVICE_LINK.fullmatch(name)


@pytest.mark.parametrize("name", ["PREVIOUSLY_NAME", "PREVIOUSLY_ENV_PREVIOUSLY_DSN"])
def test_the_docker_pattern_matches_the_two_forms_kubernetes_does_not_set(name: str) -> None:
    assert DOCKER_LINK.fullmatch(name)
    assert not DOCKER_LINK.fullmatch("PREVIOUSLY_MCP_CLIENT")
