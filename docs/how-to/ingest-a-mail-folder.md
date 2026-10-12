(ingest-a-mail-folder)=

# How to take in the mail of a folder

This guide shows you how to set up a mail folder for Previously, take its mail into the log, read several folders or mailboxes, read what the run says, run it on a schedule, and erase a mail again.
It uses a Mailu mailbox; any IMAP server that speaks TLS on port 993 works the same way.
For what a mail turns into, see {ref}`mail-mapping`, and for why, see {ref}`connectors`.

You need a database that `previously migrate` has brought up to date, and a blob store with a key: {ref}`run-a-blob-store-on-your-machine` and {ref}`keep-the-blob-key-safe` give you both.

## Create a mailbox of its own

In the Mailu admin interface, add a user to your mail domain for Previously alone, such as `previously@example.org`.
Give it a password of its own, in ASCII characters: `previously` sends the login in ASCII only, and refuses any other character.

A mailbox of its own means that the password Previously holds opens that one mailbox and nothing else.
It also keeps the folder apart from anything a person reads and files every day.

## Create the folder and fill it

Add the new mailbox to your mail client beside your own, and create a folder in it, such as `Kunde Müller`.
Then copy the mails that belong in the log from your own mailbox into that folder: in most clients, you drag a mail from one account into the other with the copy modifier held.

A copy keeps the mail as it is.
If somebody else has to send you a mail for the folder, ask them to forward it **as an attachment**: Previously takes the mail inside an attachment in as a mail of its own, with its own sender, date and text.
A mail forwarded as quoted text stays the text of the forward, and its original sender and date are lost to the log.

## Set the settings

Export the four settings of the mailbox and its folder, with the values of your server and mailbox:

```shell
export PREVIOUSLY_IMAP_ADDRESS=mail.example.org
export PREVIOUSLY_IMAP_USER=previously@example.org
export PREVIOUSLY_IMAP_PASSWORD=YOUR-MAILBOX-PASSWORD
export PREVIOUSLY_IMAP_FOLDER="Kunde Müller"
```

Write the host as the server's certificate names it, followed by `:` and the port if the server doesn't speak IMAP over TLS on 993, and the folder by its full name on the server, umlauts as they are.
For a folder inside another folder, see {ref}`configuration-reference`.

Export `PREVIOUSLY_DSN`, the five settings of the blob store and `PREVIOUSLY_BLOB_RECIPIENT` as well, as {ref}`attach-and-fetch-a-file` shows.
`ingest imap` needs no directory of identities: taking mail in seals blobs and opens none.

## Take the folder in

```console
$ previously ingest imap
imap: 5 appended, 0 known, 0 variants, up to uid 4 in Kunde Müller
```

The folder held four mails, and one of them carried a forwarded mail as an attachment, so the run appended five events.
Run it again, and it finds nothing new above the UID it reached:

```console
$ previously ingest imap
imap: 0 appended, 0 known, 0 variants, up to uid 4 in Kunde Müller
```

`ingest` doesn't catch the derived views up.
Run `project`, then read the chronicle:

```console
$ previously project
chronicle       built: 5 events, up_to_id 5
source-stats    built: 5 events, up_to_id 5
$ previously chronicle --since 2026-10-06T00:00:00+00:00
3	1	2026-10-06T09:02:11+00:00	email	AM0PR01MB1234ABCD@example.org	AW: Angebot für den Relaunch
3	2	2026-10-06T09:02:11+00:00	email	AM0PR01MB1234ABCD@example.org	Hallo Jürgen,
3	3	2026-10-06T09:02:11+00:00	email	AM0PR01MB1234ABCD@example.org	danke für das Angebot. We accept the new timeline.
3	4	2026-10-06T09:02:11+00:00	email	AM0PR01MB1234ABCD@example.org	Viele Grüße  \nEva
4	1	2026-10-08T09:00:00+00:00	email	fwd-20261008@example.org	Fwd: Rechnung Oktober
4	2	2026-10-08T09:00:00+00:00	email	fwd-20261008@example.org	no readable body: attachments only
```

Each mail's first line is its subject.
The chronicle orders by the `Date` of each mail, not by when it reached the folder, and the forwarded mail inside event 4 stands at its own date, earlier than this window.

## Take in several folders

To read more than one folder of the mailbox, name each one with `--folder`, in the order you want them read:

```console
$ previously ingest imap --folder "Kunde Müller" --folder Gesendet
imap: 0 appended, 0 known, 0 variants, up to uid 4 in Kunde Müller
imap: 0 appended, 3 known, 0 variants, up to uid 2 in Gesendet
```

Each folder prints a line of its own and keeps a watermark of its own.
With `--folder`, the run ignores `PREVIOUSLY_IMAP_FOLDER`, so name that folder as well if you still want it read.
A folder you took in through `PREVIOUSLY_IMAP_FOLDER` before goes on from its watermark when you name it with `--folder`.

In this example, `Gesendet` holds two mails that also lie in `Kunde Müller`, the second one with a mail attached.
A mail that lies in two folders becomes one event, and the folder read later counts it as known.

If a folder fails, such as one whose name you mistyped, the run prints a line on standard error that starts with `Error: folder` and the folder's name, goes on with the next folder, and returns 2.
Check the name of that folder, and run the command again.
A refused login or a server out of reach stops the run at the first folder, because every other folder would meet the same error.

## Take in several mailboxes

A run reads one mailbox, and holds the password of that one mailbox only.
For a second mailbox, run `ingest imap` a second time, with the four settings of that mailbox.
Keep the settings of each mailbox in a file of its own, as the next section shows for one, and give each mailbox a schedule entry of its own.
Runs for two mailboxes may run at the same time.

## Read what the run says

Each line on standard output counts events, not mails, for the folder it names at its end:

- `appended` is what this run wrote, variants included.
- `known` is what the log already held, such as a second copy of a mail in the folder, or every mail of a folder read from the start again.
- `variants` counts the mails that arrived under a Message-ID the log holds with another content.
  Each one also prints a line on standard error, such as `variant of 20261005101500.4711@example.net: event 6`; look at that event with `previously show` and decide whether it's a mail you want.
- `up to uid` is where the next run starts.

The command returns 0 when it read every folder, and 2 when it couldn't read one or more, with one sentence on standard error for each error.
If the sentence names the login, check the user and the password; if it names the folder, check its name.
{ref}`cli-reference` lists every error.
Any other code means the run didn't end on its own terms: 137 when the memory limit killed the run, 143 when something stopped it, and 1 with a stack trace for an error `previously` doesn't know.
After an error, run the command again once the cause is gone: the run moves its watermark only past what it appended, and nothing gets taken in twice.

## Run it on a schedule

Run `ingest imap` and then `project` every 5 to 15 minutes, and never two runs of `ingest imap` for the same mailbox at once.

On a host with Docker, put the settings into a file that only root can read, such as `/etc/previously/ingest.env`, one `NAME=value` per line and without quotes, since `--env-file` takes a value as it stands, and add a line like this one with `crontab -e`, as root:

```text
*/10 * * * * flock -n /run/previously-ingest.lock sh -c 'docker run --rm --memory 768m --network previously-blobs --env-file /etc/previously/ingest.env ghcr.io/jensens/previously:VERSION ingest imap && docker run --rm --network previously-blobs --env-file /etc/previously/ingest.env ghcr.io/jensens/previously:VERSION project'
```

Put in the exact version of a release that has `ingest imap`, the first after `0.1.0a1`, and the network your database and blob store are on, as {ref}`run-the-image` describes.
`flock -n` skips a run while the last one still runs.
To read several folders, put `--folder` and a name after `ingest imap` for each folder.
For a second mailbox, add a second line with its own settings file and its own lock file, such as `/run/previously-ingest-office.lock`.
`--memory 768m` holds the largest mail Mailu accepts by default, 50 MB, with room to spare: a mail of 49.5 MiB peaked between 529 and 531 MiB in the image, measured on 2026-10-06, and a mail is taken in one at a time, so the peak doesn't grow with the number of mails.
The run writes each blob to a temporary file before it uploads it, so `/tmp` has to be writable.

In Kubernetes, the platform's operators build the same as a CronJob with `concurrencyPolicy: Forbid`, from the same image, with the same settings in a secret, the `--folder` options in its arguments, and one CronJob for each mailbox.

## Erase a mail

Erase a mail with `previously redact event`, never with `redact units`.
The subject stands in `headers` in the payload, the raw mail is a blob, and the artifact hash in the payload is unsalted, so it confirms a short text that somebody guesses; only an erasure of the event takes all three.
Follow {ref}`erase-something` for the reason, the record, and the check afterward.

A mail stands in more events than its own, and each of them holds its words:

- **Its variants.**
  A mail that arrived again under its Message-ID with another content, such as a copy from a mailing list with a footer, is an event of its own under `<Message-ID>#<16 hexadecimal characters>`, with a raw mail of its own.
- **Every mail inside it, at every depth.**
  A mail forwarded as an attachment is an event of its own, and so is a mail attached to that one.
- **Every mail it lies inside.**
  A mail that carried it as an attachment holds it whole, in its own raw mail and as the attachment, and so does a mail that carried that one.
  That mail is somebody's forward, with words of its own; if you keep it, the erased mail stays in the store inside it.

This query lists every one of them for a Message-ID, with the variants and the mails inside a mail it found, and the mails that carry any of them, at every depth.
Put the Message-ID into its second line, without angle brackets, and run it with `psql` against the database:

```sql
WITH RECURSIVE
  given(message_id) AS (VALUES ('invoice-2026-10@example.com')),
  inside(id) AS (
    SELECT key.event_id FROM source_key AS key, given
    WHERE key.source = 'email' AND key.external_id = given.message_id
    UNION
    SELECT other.event_id
    FROM inside
    JOIN source_key AS key ON key.event_id = inside.id
    JOIN source_key AS other ON other.source = 'email'
    JOIN event ON event.id = other.event_id
    WHERE event.payload ->> 'forwarded_in' = key.external_id
       OR left(other.external_id, length(key.external_id) + 1) = key.external_id || '#'
  ),
  around(id) AS (
    SELECT id FROM inside
    UNION
    SELECT carrier.event_id
    FROM around
    JOIN event ON event.id = around.id
    JOIN event_blob AS carrier ON carrier.sha256 = decode(event.payload ->> 'raw', 'hex')
    WHERE carrier.event_id <> event.id
  )
SELECT around.id, key.external_id,
       CASE WHEN around.id IN (SELECT id FROM inside) THEN 'the mail, a variant, or inside'
            ELSE 'carries one of them' END AS why,
       event.payload ->> 'raw' AS raw
FROM around
JOIN event ON event.id = around.id
JOIN source_key AS key ON key.event_id = around.id
ORDER BY around.id;
```

For the forwarded invoice of the example above, it lists event 5, the invoice, and event 4, the mail that forwarded it.
Note the `raw` addresses in your record, then erase every event the query lists.
`redact` names a blob that another event still uses, and the event:

```console
$ previously redact event 5 --reason "the customer withdrew the forwarded invoice"
redacted by event 6
blob 90f565d149463d629a8565bab0b4b595ce8bfae14e4415059ee60ca22da4e1d4 stays in the store: event 4 still uses it
$ previously redact event 4 --reason "the customer withdrew the forwarded invoice"
redacted by event 7
```

Then erase these as well:

- **The replies that quote it.**
  A reply usually quotes the mail it answers, and the quote stays in the reply after the mail is erased.
  A reply names the Message-ID of the mail it answers in `In-Reply-To`, and of the mails before it in `References`, and both stand in `headers`:

  ```sql
  SELECT DISTINCT event.id
  FROM event, jsonb_array_elements(event.payload -> 'headers') AS header
  WHERE lower(header ->> 0) IN ('in-reply-to', 'references')
    AND header ->> 1 LIKE '%<20261005101500.4711@example.net>%';
  ```

  Read each with `previously show`, and erase the ones whose quotes hold what has to go.
  A reply that quotes a mail without naming it, such as one written in a new thread, isn't found this way.

Previously never changes the folder, so the mail stays there, in the backups of the mail server, and in the mail client of everybody who received it.
Your erasure doesn't cover any of those, and if you promise it to anybody, say so; {ref}`erase-something` lists what a promise covers.

As long as the mail lies in the folder, an erasure holds only because the log knows its key.
A restore of the database to a point before the mail was taken in forgets the key, and the next run takes the mail in again; a restore to a point before the erasure brings the content back, as {ref}`restore-from-a-backup` explains.

An erasure holds for the event, not for the content.
When somebody forwards an erased mail again as an attachment, its key is known and nothing of it becomes an event again, but its bytes come back into the store as the attachment of the new mail, and the new mail may quote it: erase the new mail as well.
The query above no longer finds it, since the erasure took the payload that names the raw mail; the new mail's attachment has the address you noted, and this finds the events that name it:

```sql
SELECT event_id FROM event_blob WHERE sha256 = decode('RAW-ADDRESS-YOU-NOTED', 'hex');
```
