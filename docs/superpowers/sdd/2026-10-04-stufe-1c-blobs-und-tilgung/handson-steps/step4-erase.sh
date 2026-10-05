#!/usr/bin/env bash
# Hands-on session, step 4: a restore point, then appends and the erasures of
# `erase-something`, each noted in a record outside the database.
S=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/handson
cd "$S"
. ./env.sh
run() { echo "\$ $*"; "$@"; echo "[exit $?]"; }
note() {  # note <id> <command…>: the record the guide asks for
  local id=$1; shift
  local hash=""
  if [ "$id" != "-" ]; then hash=$(previously show "$id" | sed -n '3s/^hash=//p'); fi
  echo "$(date -u +%F)	$id	$hash	$*" >> erasures.txt
}

run previously project
previously anchor > anchors.txt
cat anchors.txt
echo "== the restore point P: a dump of the database, tip 3"
docker exec previously-handson-pg pg_dump -U previously previously > dump-P.sql
echo "dump: $(wc -l < dump-P.sql) lines"

echo "== after P"
printf "A late addition to the file.\n" > late.txt
run previously append --source email --external-id 2026-10-05-late@example.org \
    --text "A late addition is attached." --attach late.txt
printf "A file nobody will erase.\n" > orphan.txt
run previously append --source email --external-id 2026-10-05-orphan@example.org \
    --text "One more file." --attach orphan.txt

A2=$(sha256sum draft.txt | cut -d' ' -f1)

note 2 previously redact units 2 2 --reason "a deadline the client asked to keep out of the record"
run previously redact units 2 2 --reason "a deadline the client asked to keep out of the record"
note - previously redact blob "$A2" --reason "the draft is superseded and must not be kept"
run previously redact blob "$A2" --reason "the draft is superseded and must not be kept"
run previously blob get "$A2" --output draft-copy.txt
note 1 previously redact event 1 --reason "the client withdrew consent to keep the kickoff minutes"
run previously redact event 1 --reason "the client withdrew consent to keep the kickoff minutes"
note 4 previously redact event 4 --reason "the late addition was sent by mistake"
run previously redact event 4 --reason "the late addition was sent by mistake"
run previously show 2
run previously show 1
run previously verify --anchors anchors.txt --blobs
run previously log
echo "== the record kept outside the database"
cat erasures.txt
