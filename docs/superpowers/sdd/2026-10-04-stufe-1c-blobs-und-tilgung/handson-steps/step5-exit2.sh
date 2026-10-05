#!/usr/bin/env bash
# Hands-on session, step 5: an erasure whose deletion from the store fails
# (the store is down), and the second run that finishes it.
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

printf "A signed consent form.\n" > consent.txt
run previously append --source email --external-id 2026-10-05-consent@example.org \
    --text "The consent form is attached." --attach consent.txt
A=$(sha256sum consent.txt | cut -d' ' -f1)
echo "== objects in the bucket"
aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 ls "s3://$PREVIOUSLY_BLOB_BUCKET" | sed -E 's/^\S+ \S+ +//'

echo "== the store goes down"
docker stop previously-blobs >/dev/null
SECONDS=0
run previously redact event 10 --reason "the consent was withdrawn"
echo "(took ${SECONDS}s)"
run previously show 10
echo "== the store comes back"
docker start previously-blobs >/dev/null
sleep 5
run previously verify --blobs
run previously redact event 10 --reason "the consent was withdrawn"
run previously verify --blobs
echo "== objects in the bucket"
aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 ls "s3://$PREVIOUSLY_BLOB_BUCKET" | sed -E 's/^\S+ \S+ +//'
echo "consent address: $A"
