# One-shot Codex wakes

`wake.sh` manages schedules; `wake_run.sh` delivers them. Requires macOS, a logged-in
GUI user, Python 3.9+ and Codex on PATH. Bash owns the command array, retries and
completion trap; embedded Python handles timezone conversion, JSON, plist and an
advisory lock. The canonical concept is `wake`; no existing names were replaced.

## Usage (README excerpt, five lines)

```sh
ops/wake.sh add '2026-11-01T05:00+09:00' <UUID-or-exact-name> prompt.txt --name earnings
ops/wake.sh add '05:00' <UUID-or-exact-name> prompt.txt --mode resume # JST; past HH:MM means tomorrow
WAKE_DRY=1 ops/wake.sh add '05:00' <UUID-or-exact-name> prompt.txt --name dry
ops/wake.sh list
ops/wake.sh cancel <id>
```

`--mode resume` is the default; `queue` requires explicit selection. `add` captures
the caller's cwd, Codex executable, PATH, optional CODEX_HOME path, sandbox
`workspace-write`, approval `never`, and writable roots (cwd plus its git common
directory). Call from the target project. No credentials are copied. Exact names
are resolved read-only through Codex's local `state_5.sqlite` `threads.name`;
ambiguous/missing names fail with instructions to use a UUID. This schema is
version-specific. UUIDs can be scheduled without an existing local record.

ISO input requires a timezone and rejects past instants. Calendar scheduling has
minute precision: seconds round UP. Deduplication uses resolved UUID and scheduled
minute, under a lock; cancelled schedules can be replaced with a different name.
IDs use JST time and name (default: first eight UUID characters). Reusing an ID
fails rather than overwriting its history. Host-local calendar fields are generated
from the absolute instant; reschedule if the host timezone changes afterward.

Each directory contains a prompt copy, 0600 spec, private logs, and last response.
The LaunchAgent plist is also 0600. `ops/wakes/.gitignore` ignores per-wake
directories and the lock; source documentation stays tracked. Registry uses the
existing `t`, `name`, `event`, `rc` conventions, adding id, target and mode:
`wake_scheduled`, `wake_fired` (with `delay_minutes`), `wake_capacity`,
`wake_result` (with rc), `wake_cancelled`, and `wake_schedule_failed`.
`list` shows all scheduled/running wakes plus the latest 20 terminal records.

Resume reads the prompt from stdin (`-`); queue passes it as one quoted array
argument. Neither uses eval or shell interpolation of message contents. Capacity
responses retry six times with 600-second gaps (`WAKE_TRIES` / `WAKE_GAP` overrides
for direct runner tests). Exhaustion records rc=75. Queue success means accepted,
not proof of consumption. Dry runs persist at scheduling time and log commands
without calling Codex. Final status and plist deletion precede bootout because
bootout may terminate its own runner. A hard kill or power loss can leave `running`
state: the claim guard prevents replay; inspect logs and use `cancel` only after
resolving the interrupted state. Cancellation deliberately refuses running turns.
Cleanup failures are visible in `launch.log`; `cancel` can retry unloading terminal
jobs. These are one-shot jobs, not a crash-recovery daemon.

## Queue evidence and sleep semantics (2026-10-30)

Local `codex-cli 0.155.1`, `codex queue --help`:

> Queue a message for an existing session

The help accepts `--thread` as a UUID or exact session name, but exposes no consumer
liveness/acknowledgement operation. `codex exec resume --help` explicitly accepts a
session ID/name and a prompt; `-` reads stdin. The [official Remote article](https://developers.openai.com/blog/mastering-codex-remote-for-engineering)
describes Queue as waiting for the current response to finish before the next turn;
it does not establish CLI queue consumption with no open client. Binary strings
also contain “resume the thread before starting a queued message”, but a string
alone does not establish that command's execution path. There is insufficient
verified evidence to promise unattended queue consumption or detect it reliably.
Consequently this implementation does not guess from process presence; it defaults
to an explicit headless resume. Resume can still fail due to permissions, network,
authentication or capacity; rc and logs capture the outcome.

The installed macOS `man launchd.plist`, `StartCalendarInterval`, explicitly says:
“launchd will start the job the next time the computer wakes up.” It also specifies
that multiple missed intervals coalesce into one event. This confirms sleep/wake
catch-up, not automatic power-on or a power-off guarantee. Delay is actual claim
time minus scheduled epoch, in fractional minutes. Month/day/hour/minute have no
year field, hence removal after execution is essential.

## Verification

`bash -n ops/wake.sh ops/wake_run.sh ops/test_wake.sh`, ShellCheck, and
`ops/test_wake.sh` check time parsing, past/invalid rejection, tomorrow rollover,
UUID/name deduplication, permissions, cancellation, early/repeated execution,
dry mode, command delivery, injection resistance, result/cleanup, and capacity
exhaustion. The shell test uses a temporary HOME, fake launchctl/Codex and isolated
registry; these results must not be described as real launchd or model execution.

Real attempts in this restricted agent environment:

- Dry wake requested for 2026-10-30 18:34 JST (approximately two minutes ahead).
  `add` failed with `Operation not permitted` writing
  `~/Library/LaunchAgents/com.prts.wake.20261030T1834-verify-dry.plist`.
  Spec is `failed`, rc=1, with `wake_schedule_failed`; no job was bootstrapped.
- Disposable session creation using `codex exec -C /Users/prts/PRTS -s
  workspace-write -c 'approval_policy="never"' --json 'Reply only pong. Do not use
  tools.'` failed with `failed to initialize in-process app-server client:
  Operation not permitted`. No test session ID was returned, so a real resume
  wake could not be scheduled. No existing session was used.

Raw attempt logs are in ignored `ops/wakes/verification/`. Both requested real
end-to-end checks remain unverified, blocked by environment permissions, not
replaced by the mocked tests. To repeat from an unrestricted user terminal: create
that disposable pong session, take its `thread.started` UUID, schedule separate
dry and resume wakes at least two minutes ahead, then inspect `wake_fired`,
`wake_result`, `last.md`, spec status, plist absence and `launchctl print` absence.
The transcript must show a new completed turn for that same disposable UUID.

`ops/README.md` is intentionally untouched because the controller owns its edit.
