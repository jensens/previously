#!/usr/bin/env bash
# Hands-on session, step 7: what an operator sees when a setting is missing or
# wrong, and then the clean-up of the guide plus the session's own containers.
S=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/handson
cd "$S"
. ./env.sh
run() { echo "\$ $*"; "$@"; echo "[exit $?]"; }
A3=$(sha256sum agenda.txt | cut -d' ' -f1)

echo "== blob get without the directory of identities"
( unset PREVIOUSLY_BLOB_IDENTITIES; run previously blob get "$A3" --output a.txt )
echo "== blob get with a directory that lacks the identity"
mkdir -p empty-identities
( export PREVIOUSLY_BLOB_IDENTITIES=$PWD/empty-identities; run previously blob get "$A3" --output a.txt )
echo "== verify --blobs with a wrong secret"
( export PREVIOUSLY_BLOB_SECRET_KEY=0000000000000000; run previously verify --blobs )
echo "== append --attach with a file that is not there"
run previously append --source email --external-id 2026-10-05-none@example.org --text "Nothing." --attach nothing.txt
echo "== append --attach without a recipient"
( unset PREVIOUSLY_BLOB_RECIPIENT; run previously append --source email --external-id 2026-10-05-none@example.org --text "Nothing." --attach agenda.txt )
echo "== blob get into a file that exists"
run previously blob get "$A3" --output agenda.txt
echo "== blob get with something that is no address"
run previously blob get nonsense --output a.txt
echo "== redact units at an event that has no such unit"
run previously redact units 3 9 --reason "a test"
echo "== redact with an empty reason"
run previously redact event 3 --reason " "
echo "== the log is as it was"
run previously log
ls a.txt 2>/dev/null || echo "no a.txt was written"

echo "== Remove the server (the guide), and the session's own containers"
docker rm -f -v previously-blobs
docker network rm previously-blobs
docker rm -f -v previously-handson-pg previously-handson-age
cd /
rm -rf "$S"
echo "session directory removed, with its keys and its secret"
