#!/usr/bin/env bash
# Hands-on addendum: `project` in a loop beside appends and erasures, to see
# by hand what the serialized catch-up does; then the clean-up.
S=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/handson
W=/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1c-blobs
cd "$S"
. ./env.sh

echo "=== the help of redact"
previously redact --help | sed -n '/positional/,$p'

echo "=== H. project in a loop beside 25 appends and 25 erasures, on a fresh database"
docker exec previously-handson-pg psql -q -U previously -d postgres \
    -c "DROP DATABASE previously" -c "CREATE DATABASE previously OWNER previously"
( cd "$W" && uv run alembic upgrade head >/dev/null 2>&1 )
: > project.out
: > project.err
(
  while [ ! -e stop ]; do
    previously project >> project.out 2>> project.err
    echo "[exit $?]" >> project.out
  done
) &
LOOP=$!
: > redact.err
for i in $(seq 1 25); do
  id=$(previously append --source smoke --external-id "h-$i" --text "Secret line one of $i.

Secret line two of $i.")
  previously redact event "$id" --reason "smoke $i" >> redact.out 2>> redact.err
  echo "[exit $?]" >> redact.out
done
touch stop
wait $LOOP
previously project > /dev/null 2>> project.err
echo "project runs: $(grep -c '^\[exit' project.out), exit codes: $(grep '^\[exit' project.out | sort | uniq -c | tr '\n' ' ')"
echo "redact runs:  $(grep -c '^\[exit' redact.out), exit codes: $(grep '^\[exit' redact.out | sort | uniq -c | tr '\n' ' ')"
echo "tracebacks in project: $(grep -c Traceback project.err), in redact: $(grep -c Traceback redact.err)"
echo "distinct lines on project's standard error:"
sort project.err | uniq -c | cut -c1-220
echo "distinct lines on redact's standard error:"
sort redact.err | uniq -c | cut -c1-220
echo "events in the log: $(previously log | wc -l)"
echo "rows in the chronicle that still carry text: $(previously chronicle | grep -c 'Secret line')"
previously project
previously verify

echo "=== clean-up"
docker rm -f -v previously-blobs previously-handson-pg previously-handson-age
docker network rm previously-blobs
cd /
rm -rf "$S"
echo "session directory removed, with its key and its secret"
