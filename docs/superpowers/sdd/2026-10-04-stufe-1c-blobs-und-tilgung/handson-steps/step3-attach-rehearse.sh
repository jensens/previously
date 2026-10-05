#!/usr/bin/env bash
# Hands-on session, step 3: `attach-and-fetch-a-file`, `verify --blobs`, the
# rehearsal and the key change of `keep-the-blob-key-safe`.
S=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/handson
cd "$S"
. ./env.sh
U="$(id -u):$(id -g)"
age() { docker exec --user "$U" -w "$PWD" previously-handson-age age "$@"; }
age-keygen() { docker exec --user "$U" -w "$PWD" previously-handson-age age-keygen "$@"; }
aws() {
  docker run --rm --network host --user "$U" -e HOME=/tmp -v "$S:$S" -w "$PWD" \
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION \
    amazon/aws-cli:2.37.9 "$@"
}
run() { echo "\$ $*"; "$@"; echo "[exit $?]"; }

printf "Kickoff minutes: the client approved the new homepage design.\n" > minutes.txt
run previously append --source email --external-id 2026-10-05-minutes@example.org \
    --text "The minutes of the kickoff are attached." --attach minutes.txt
run previously show 1
A1=$(sha256sum minutes.txt | cut -d' ' -f1)
run previously blob get "$A1" --output minutes-copy.txt
run cmp minutes.txt minutes-copy.txt
ls -l minutes-copy.txt | cut -d' ' -f1
run previously verify --blobs

echo "== Rehearse the backup (the identity comes from a copy made as a backup would be)"
mkdir -p backup rehearsal
cp identities/* backup/
cp "backup/$PREVIOUSLY_BLOB_RECIPIENT" rehearsal/identity.txt
cd rehearsal
export AWS_ACCESS_KEY_ID=$PREVIOUSLY_BLOB_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=$PREVIOUSLY_BLOB_SECRET_KEY
export AWS_DEFAULT_REGION=$PREVIOUSLY_BLOB_REGION
run aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 cp --no-progress "s3://$PREVIOUSLY_BLOB_BUCKET/$A1" blob.age
head -c 21 blob.age; echo
run age -d -i identity.txt -o content blob.age
run sha256sum content
echo "address:  $A1"
cd "$S"

echo "== Change the key"
OLD=$PREVIOUSLY_BLOB_RECIPIENT
age-keygen -o key.txt
mv key.txt "identities/$(age-keygen -y key.txt)"
ls identities
NEW=$(ls identities | grep -v "$OLD")
sed -i "s/^export PREVIOUSLY_BLOB_RECIPIENT=.*/export PREVIOUSLY_BLOB_RECIPIENT=$NEW/" env.sh
. ./env.sh
cp identities/* backup/

printf "Second draft of the homepage copy.\n" > draft.txt
run previously append --source email --external-id 2026-10-05-draft@example.org \
    --text "The second draft is attached.

The client wants it by Friday." --attach draft.txt
printf "Agenda: budget, timeline, open questions.\n" > agenda.txt
run previously append --source email --external-id 2026-10-05-agenda@example.org \
    --text "The agenda is attached." --attach agenda.txt
run previously verify --blobs

echo "== the object names its recipient; the old identity does not open it"
A2=$(sha256sum draft.txt | cut -d' ' -f1)
cd rehearsal
aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3api head-object --bucket "$PREVIOUSLY_BLOB_BUCKET" --key "$A2" | grep -A2 Metadata
echo "new recipient: $NEW"
aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 cp --no-progress "s3://$PREVIOUSLY_BLOB_BUCKET/$A2" blob2.age
run age -d -i identity.txt -o content2 blob2.age
rm -f content blob.age blob2.age identity.txt content2
cd "$S"
