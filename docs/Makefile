# Documentation targets. Every tool comes out of the project's own venv, so
# uv.lock is the only place a version is pinned (CLAUDE.md).

SPHINXOPTS  = -W --keep-going
QUADRANTS   = index.md tutorials how-to reference explanation

.PHONY: help html linkcheck vale clean

help:
	@echo "html       build the HTML documentation, warnings are errors"
	@echo "linkcheck  check that every link resolves"
	@echo "vale       check style, spelling and American English"
	@echo "clean      remove the build directory"

html:
	uv run --extra docs sphinx-build $(SPHINXOPTS) -b html . _build/html

linkcheck:
	uv run --extra docs sphinx-build $(SPHINXOPTS) -b linkcheck . _build/linkcheck

# `.vale.ini` declares `Packages = Microsoft`, but Vale does not fetch a
# declared package on its own — it has to be synced first, or the run fails
# with a missing-styles error. `vale sync` does that fetch, and it reaches
# out to the network, so it is not something this target should do on every
# local run. Only `.vale-styles/Microsoft/` — what `vale sync` fetches — is on
# .gitignore (task 2, fix round 1: the project vocabulary under
# `.vale-styles/config/vocabularies/Previously/` is committed, so a blanket
# `.vale-styles/` ignore swallowed it too). A fresh checkout starts without
# the synced package: sync once there, then reuse the cached directory on
# every later run. The CI gate (`.github/workflows/gates.yml`) gets a fresh
# checkout every time, so it pays this fetch on every run too — that run has
# network access, so it is a fair price there.
vale:
	cd .. && test -d .vale-styles/Microsoft || uv run --extra docs vale sync
	cd .. && uv run --extra docs vale $(addprefix docs/,$(QUADRANTS))

clean:
	rm -rf _build
