#!/usr/bin/env bash
# Hands-on addendum after the code fix wave: the behaviors the wave changed,
# and the restore case the documentation review described.
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
bucket() { aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 ls "s3://$PREVIOUSLY_BLOB_BUCKET" | sed -E 's/^\S+ \S+ +\S+ //' | cut -c1-12; }
# run: the command, then its standard output and standard error apart
run() {
  echo "\$ $*"
  "$@" > .out 2> .err
  local rc=$?
  sed 's/^/  out| /' .out
  sed 's/^/  err| /' .err
  echo "  [exit $rc]"
}

echo "=== A. redact units says that the payload stays"
run previously append --source note --external-id a-1 --text "First paragraph.

Second paragraph, to be erased."
run previously project
run previously redact units 1 2 --reason "a test of the notice"
run previously redact units 1 2 --reason "a test of the notice"
run previously redact units --help

echo "=== B. the store is down while an event with a blob is erased"
printf "A signed consent form.\n" > consent.txt
run previously append --source note --external-id b-1 --text "The consent form is attached." --attach consent.txt
run previously project
docker stop previously-blobs >/dev/null
run previously redact event 3 --reason "the consent was withdrawn"
echo "-- the chronicle, while the store is still down:"
run previously chronicle
docker start previously-blobs >/dev/null
sleep 5
run previously redact event 3 --reason "the consent was withdrawn"
echo "-- objects in the bucket: $(bucket | tr '\n' ' ')"

echo "=== F. a blob erased before the restore point and attached again after it"
printf "A file that comes back.\n" > b.txt
B=$(sha256sum b.txt | cut -d' ' -f1)
run previously append --source note --external-id f-1 --text "A file." --attach b.txt
run previously redact blob "$B" --reason "must not be kept"
docker exec previously-handson-pg pg_dump -U previously previously > dump-P.sql
run previously append --source note --external-id f-2 --text "The same file again." --attach b.txt
echo "-- objects in the bucket before the restore: $(bucket | tr '\n' ' ') (b.txt is ${B:0:12})"
docker exec previously-handson-pg psql -q -U previously -d postgres \
    -c "DROP DATABASE previously" -c "CREATE DATABASE previously OWNER previously"
docker exec -i previously-handson-pg psql -q -U previously -d previously < dump-P.sql > /dev/null
echo "-- restored to the dump"
run previously verify --blobs
run previously redact blob "$B" --reason "must not be kept"
run previously verify --blobs
echo "-- objects in the bucket after the repeat: $(bucket | tr '\n' ' ')"

echo "=== E. append --attach without the database setting stores nothing"
printf "A file that must not be uploaded.\n" > e.txt
( unset PREVIOUSLY_DSN; run previously append --source note --external-id e-1 --text "x" --attach e.txt )
echo "-- objects in the bucket: $(bucket | tr '\n' ' ') (e.txt would be $(sha256sum e.txt | cut -c1-12))"
echo "=== G. an address that is no address comes before a missing database setting"
( unset PREVIOUSLY_DSN; run previously blob get nonsense --output x.txt )
( unset PREVIOUSLY_DSN; run previously redact blob nonsense --reason "x" )

echo "=== D. the identity directory is no directory"
printf "One more file.\n" > d.txt
run previously append --source note --external-id d-1 --text "One more." --attach d.txt
D=$(sha256sum d.txt | cut -d' ' -f1)
( export PREVIOUSLY_BLOB_IDENTITIES=$S/nowhere; run previously verify --blobs )
( export PREVIOUSLY_BLOB_IDENTITIES=$S/nowhere; run previously blob get "$D" --output d-copy.txt )
mkdir -p empty
echo "-- and an existing directory that lacks the identity:"
( export PREVIOUSLY_BLOB_IDENTITIES=$S/empty; run previously verify --blobs )

echo "=== C. a chain finding is not hidden by a store that is down"
docker exec previously-handson-pg psql -q -U previously -c "UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 1"
run previously verify --blobs
docker stop previously-blobs >/dev/null
run previously verify --blobs
docker start previously-blobs >/dev/null
sleep 5
