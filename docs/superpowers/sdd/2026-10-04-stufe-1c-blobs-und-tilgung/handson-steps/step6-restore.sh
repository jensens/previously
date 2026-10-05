#!/usr/bin/env bash
# Hands-on session, step 6: restore the database to P (tip 3) and follow
# `restore-from-a-backup`, section "Check the blobs, and repeat the erasures".
S=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/handson
cd "$S"
. ./env.sh
U="$(id -u):$(id -g)"
aws() {
  docker run --rm --network host --user "$U" -e HOME=/tmp -v "$S:$S" -w "$PWD" \
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION \
    amazon/aws-cli:2.37.9 "$@"
}
export AWS_ACCESS_KEY_ID=$PREVIOUSLY_BLOB_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=$PREVIOUSLY_BLOB_SECRET_KEY
export AWS_DEFAULT_REGION=$PREVIOUSLY_BLOB_REGION
run() { echo "\$ $*"; "$@"; echo "[exit $?]"; }
A2=$(sha256sum draft.txt | cut -d' ' -f1)

echo "== the restore: the database goes back to the dump taken at P"
docker exec previously-handson-pg psql -q -U previously -d postgres \
    -c "DROP DATABASE previously" -c "CREATE DATABASE previously OWNER previously"
docker exec -i previously-handson-pg psql -q -U previously -d previously < dump-P.sql > /dev/null
echo "[restore exit $?]"

echo "== the chain check"
run previously verify --anchors anchors.txt --exact

echo "== Check the blobs"
run previously verify --blobs
run previously show 1
run previously chronicle

echo "== Learn the tip"
run previously anchor

echo "== the record"
cat erasures.txt

echo "== blob erasures first, before anything else appends"
run previously redact blob "$A2" --reason "the draft is superseded and must not be kept"

echo "== record line: units of event 2 — compare the hash"
previously show 2 | sed -n '3p'
grep -P '^\S+\t2\t' erasures.txt | cut -f3
run previously redact units 2 2 --reason "a deadline the client asked to keep out of the record"

echo "== record line: event 1 — compare the hash"
previously show 1 | sed -n '3p'
grep -P '^\S+\t1\t' erasures.txt | cut -f3
run previously redact event 1 --reason "the client withdrew consent to keep the kickoff minutes"

echo "== record line: event 4 — its id lies above the tip learned (3): it lost its target"
echo "   what show 4 says now, and the hash in the record:"
run previously show 4
grep -P '^\S+\t4\t' erasures.txt | cut -f3
echo "   what the command would do if somebody repeated it by its id alone:"
run previously redact event 4 --reason "the late addition was sent by mistake"

echo "== Then run verify --blobs again"
run previously verify --anchors anchors.txt --blobs
run previously chronicle
run previously log
echo "== objects in the bucket"
aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 ls "s3://$PREVIOUSLY_BLOB_BUCKET" | sed -E 's/^\S+ \S+ +//'
echo "agenda: $(sha256sum agenda.txt | cut -d' ' -f1)"
echo "orphan: $(sha256sum orphan.txt | cut -d' ' -f1)"
