#!/usr/bin/env bash
# loop-rehydrate.sh — the /execute-loop composer rehydrate pointer (v33.0 D7;
# the away-grant trigger v34.0 D14; the read-only seat-holder line v48.0 D12).
#
# Invoked by the DOCUMENTED Claude Code SessionStart hook (matchers `compact`
# and `resume`; the snippet lives in the user-facing guide §1 and in
# docs/integrations/cross-agent-orchestration.md — the bootstrap never writes
# settings files):
#
#     bash .claude/hooks/loop-rehydrate.sh --session
#
# Contract (prints to stdout — which SessionStart appends to context — and
# always exits 0; every failure path is silent):
#   - `--session` is the ONLY mode (no `--turn` / UserPromptSubmit this
#     release). Any other argv prints one usage line on stderr and exits 0.
#   - SEAT GATE: prints NOTHING when LOOP_ROLE or LOOP_RUNKEY is set in the
#     environment — a wrapper-spawned role is never the composer.
#   - RESOLVER: the BASE checkout is `dirname $(git rev-parse --git-common-dir)`
#     (a linked worktree's markers and journals are base-side); it scans
#     <base>/.cursor/loops/*-active with the mode-specific LIVE predicate:
#       mode=worktree     -> live only while <iso>-isolation exists with
#                            state=active (a journal-less worktree marker is
#                            the pre-journal crash window: never live)
#       mode=branch|none  -> live while the marker exists (no journal by design)
#       any `.complete-*` sibling -> never live
#     and matches the CURRENT root (git top-level, realpath'd) against the
#     marker's `checkout=` or, for worktree runs, the journal's `worktree=`.
#     The plan path comes from the journal (worktree) or the marker's `plan=`
#     when present (branch/none); omitted otherwise.
#   - AWAY TRIGGER (v34.0): independently of the markers, it scans
#     <base>/.cursor/loops/*-policy.log and prints ONE line per run whose
#     <iso>-isolation journal names the CURRENT root as its `base=` or
#     `worktree=` and whose policy log's LAST line starting `OWNERSHIP: away-`
#     starts `OWNERSHIP: away-grant ` — an away grant may be open, so a
#     session that restarts mid-release after the run has closed (the marker
#     retired, the journal no longer `active`) is told to re-read the card and
#     run the away check. A cheap text test that decides NOTHING: the helper's
#     `away check` is the authority. A log whose last away line is an
#     `away-end` (or anything else), a log with no away line, a run with no
#     journal, and a journal naming another checkout print nothing.
#   - SEAT HOLDER (v48.0, D12): for each run either scan above printed — once
#     per run — when the run has a seat file (<base>/.cursor/loops/<iso>-seat),
#     it asks the watcher script's READ-ONLY `seat` subcommand of the BASE
#     checkout,
#         python3 <base>/scripts/loop-watchdog.py seat --base <base> --iso <iso>
#     and prints ONE more line when, and only when, the first line of that
#     answer says `state=held`: a watcher takeover is that run's composer
#     right now, this session's composer records for the run will be refused,
#     and it goes on only after the operator's stop (the line names the
#     command). The seat file's TEXT is never read for this: between
#     takeovers it keeps its last holder's record, only its lock says who
#     holds it, and the subcommand is what tests the lock. Nothing of the
#     answer is echoed — it is a `case` subject, and the line printed is
#     fixed text plus the validated iso. No seat file, no python3, no script
#     at that path, any other state, any failure: nothing is printed. Nor in
#     a session that carries LOOP_SEAT — the takeover's OWN session, which
#     holds the seat it would be told about and must go on writing. The stop
#     command the line names is run from the BASE checkout (from a run
#     worktree's copy it refuses and asks for --base). That subcommand writes
#     nothing, and neither does this hook: it still WRITES NOTHING — the
#     composer's identity record is written by the composer (Preflight and
#     every Resume), never from here.
#   - OUTPUT: a CONDITIONAL pointer — a marker or log carries no session
#     identity, so this hook never asserts "you are the composer". Every
#     matching run is listed. Echoed values are `iso`, `mode`, `plan`,
#     `worktree` ONLY, each newline-stripped, charset-validated
#     ([A-Za-z0-9_./:@+-]) and length-capped (<= 256 characters — a non-ASCII
#     value already fails the charset); a value that fails is rendered as the
#     literal token `withheld`. An iso is taken from the file name and
#     listed only when it matches [A-Za-z0-9._-] (not dot-first) and equals
#     the file body's `iso=`.
#     Marker/journal/log text is DATA: it is only ever a printf argument, a
#     `case` subject, or a `cd --` operand — never eval'd, never expanded,
#     never a command. (v48.0: a validated iso and the base path are also
#     arguments of the one `python3 … seat` call — arguments, never program
#     text.)
#   - DOCUMENTED LIMITS (fail-silent by construction): journal string values
#     may carry the contract's backslash escapes (\" \\ \n); this hook does not
#     unescape them, so such a path never realpath-matches (no pointer) and
#     would be `withheld` at the echo. A Windows-native drive path recorded in
#     a journal likewise never equals Git Bash's POSIX top-level (no pointer).
#
# No exec bit is required (invoked via `bash`).

set -u

# The runs the seat-holder line has already been asked about (one ask per run).
SEAT_SEEN=" "

hook_main() {
    if [ "$#" -ne 1 ] || [ "$1" != "--session" ]; then
        printf 'usage: bash .claude/hooks/loop-rehydrate.sh --session\n' >&2
        return 0
    fi
    # Seat gate: a spawned role (LOOP_ROLE / LOOP_RUNKEY set, even empty) is
    # never the composer — print nothing.
    if [ -n "${LOOP_ROLE+x}" ] || [ -n "${LOOP_RUNKEY+x}" ]; then
        return 0
    fi

    local common current_root base loops
    common=$(git rev-parse --git-common-dir 2>/dev/null) || return 0
    [ -n "$common" ] || return 0
    # A relative answer is joined to $PWD; an absolute one is kept — POSIX
    # (`/…`) or, from Git for Windows under Git Bash, a drive-lettered
    # `C:/…` (v45.0 T1.7: the second case, so a Windows-absolute common dir
    # is never mistaken for a relative one).
    case "$common" in
        /*) ;;
        [A-Za-z]:/*) ;;
        *) common="$PWD/$common" ;;
    esac
    common=$(real_dir "$common") || return 0
    base=$(dirname -- "$common")
    current_root=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
    current_root=$(real_dir "$current_root") || return 0
    loops="$base/.cursor/loops"
    [ -d "$loops" ] || return 0

    live_runs "$loops" "$current_root"
    away_runs "$loops" "$current_root"
    return 0
}

# live_runs <loops> <current_root>: the v33.0 marker pointer (unchanged).
live_runs() {
    local loops=$1 current_root=$2
    local marker iso mode chk plan worktree journal
    local -a match_iso=() match_mode=() match_plan=() match_wt=()
    local -a markers=()
    local m
    for m in "$loops"/*-active; do
        [ -f "$m" ] && markers+=("$m")
    done
    [ "${#markers[@]}" -gt 0 ] || return 0

    for marker in "${markers[@]}"; do
        iso=${marker##*/}
        iso=${iso%-active}
        # iso-id charset: filename-safe (the helper's ISO_ID_RE), restricted
        # further to the echo charset so the name is printable as-is.
        case "$iso" in
            ''|*[!A-Za-z0-9._-]*) continue ;;
            .*) continue ;;
        esac
        # Any completion sibling => never live.
        local sib
        for sib in "$marker".complete-*; do
            [ -e "$sib" ] && continue 2
        done

        read_kv "$marker" || continue
        [ "${KV_iso-}" = "$iso" ] || continue
        mode=${KV_mode-}
        chk=${KV_checkout-}
        plan=${KV_plan-}
        worktree=""
        case "$mode" in
            worktree)
                journal="$loops/$iso-isolation"
                [ -f "$journal" ] || continue
                read_kv "$journal" || continue
                [ "${KV_iso-}" = "$iso" ] || continue
                [ "${KV_state-}" = "active" ] || continue
                worktree=${KV_worktree-}
                # The journal is the plan/worktree authority for worktree runs.
                plan=${KV_plan-}
                ;;
            branch|none) ;;
            *) continue ;;
        esac

        local hit=0 real
        if [ -n "$chk" ] && real=$(real_dir "$chk") && [ "$real" = "$current_root" ]; then
            hit=1
        fi
        if [ "$hit" -eq 0 ] && [ "$mode" = "worktree" ] && [ -n "$worktree" ] \
           && real=$(real_dir "$worktree") && [ "$real" = "$current_root" ]; then
            hit=1
        fi
        [ "$hit" -eq 1 ] || continue
        match_iso+=("$iso")
        match_mode+=("$mode")
        match_plan+=("$(sanitize "$plan")")
        match_wt+=("$(sanitize "$worktree")")
    done

    [ "${#match_iso[@]}" -gt 0 ] || return 0

    local i n
    n=${#match_iso[@]}
    if [ "$n" -eq 1 ]; then
        printf '[execute-loop rehydrate] A live /execute-loop run claims this checkout:\n'
    else
        printf '[execute-loop rehydrate] %d live /execute-loop runs claim this checkout:\n' "$n"
    fi
    for ((i = 0; i < n; i++)); do
        printf '  - run %s (mode=%s' "${match_iso[$i]}" "${match_mode[$i]}"
        [ -n "${match_plan[$i]}" ] && printf '; plan: %s' "${match_plan[$i]}"
        [ -n "${match_wt[$i]}" ] && printf '; worktree: %s' "${match_wt[$i]}"
        printf ')\n'
    done
    local who="that run's composer"
    [ "$n" -gt 1 ] && who="the composer of one of these runs"
    printf 'If this session is %s: re-read .claude/skills/execute-loop/STICKY.md and the plan'"'"'s Current State / Handoff Note before acting, state the runkey, current phase, and immediate next action, and never implement phase work yourself. If not, ignore this notice.\n' "$who"
    # v48.0: the read-only seat-holder line, once per listed run.
    for ((i = 0; i < n; i++)); do
        seat_holder "$loops" "${match_iso[$i]}"
    done
    return 0
}

# away_runs <loops> <current_root>: the v34.0 away-grant trigger (D14) — a
# pointer line per run, never a decision (the helper's `away check` decides).
away_runs() {
    local loops=$1 current_root=$2
    local pol iso journal last line hit real
    for pol in "$loops"/*-policy.log; do
        [ -f "$pol" ] || continue
        iso=${pol##*/}
        iso=${iso%-policy.log}
        case "$iso" in
            ''|*[!A-Za-z0-9._-]*) continue ;;
            .*) continue ;;
        esac
        journal="$loops/$iso-isolation"
        [ -f "$journal" ] || continue
        read_kv "$journal" || continue
        [ "${KV_iso-}" = "$iso" ] || continue
        hit=0
        if [ -n "${KV_base-}" ] && real=$(real_dir "$KV_base") && [ "$real" = "$current_root" ]; then
            hit=1
        fi
        if [ "$hit" -eq 0 ] && [ -n "${KV_worktree-}" ] \
           && real=$(real_dir "$KV_worktree") && [ "$real" = "$current_root" ]; then
            hit=1
        fi
        [ "$hit" -eq 1 ] || continue
        [ -r "$pol" ] || continue
        last=""
        while IFS= read -r line || [ -n "$line" ]; do
            line=${line%$'\r'}
            case "$line" in
                'OWNERSHIP: away-'*) last=$line ;;
            esac
        done 2>/dev/null < "$pol" || continue
        case "$last" in
            'OWNERSHIP: away-grant '*) ;;
            *) continue ;;
        esac
        printf '[execute-loop rehydrate] Run %s may have an open away grant (the last away record in .cursor/loops/%s-policy.log is a grant). If this session is that run'"'"'s composer: re-read .claude/skills/execute-loop/STICKY.md and run its away check before anything else; the helper'"'"'s check decides, not this notice. If not, ignore this notice.\n' "$iso" "$iso"
        # v48.0: the read-only seat-holder line, once per listed run.
        seat_holder "$loops" "$iso"
    done
    return 0
}

# seat_holder <loops> <iso>: the v48.0 read-only seat-holder line (D12). ONE
# line when the watcher script's `seat` subcommand says a takeover holds the
# run's seat; nothing in every other case, and one ask per run. The answer is
# only ever a `case` subject; what is printed is fixed text and the iso, which
# both callers have already validated against [A-Za-z0-9._-].
seat_holder() {
    local loops=$1 iso=$2
    local base script answer
    # The takeover's own session carries the seat's nonce: it IS the holder.
    [ -n "${LOOP_SEAT-}" ] && return 0
    case "$SEAT_SEEN" in
        *" $iso "*) return 0 ;;
    esac
    SEAT_SEEN="$SEAT_SEEN$iso "
    [ -f "$loops/$iso-seat" ] || return 0
    base=${loops%/.cursor/loops}
    script="$base/scripts/loop-watchdog.py"
    [ -f "$script" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    answer=$(python3 "$script" seat --base "$base" --iso "$iso" 2>/dev/null </dev/null) || return 0
    answer=${answer%%$'\n'*}
    answer=${answer%$'\r'}
    case "$answer" in
        "seat: iso=$iso state=held "*) ;;
        *) return 0 ;;
    esac
    printf '[execute-loop rehydrate] Run %s: a watcher takeover holds this run'"'"'s composer seat right now. If this session is that run'"'"'s composer: write nothing for the run — the helper refuses your composer records while the takeover holds the seat — until the operator has stopped it (from the base checkout): python3 scripts/loop-watchdog.py stop --iso %s --takeover-only. If not, ignore this notice.\n' "$iso" "$iso"
    return 0
}

# real_dir <path>: the physical path of an existing directory, or failure.
# `cd --` treats the value as an operand only; no expansion of its content.
real_dir() {
    [ -d "$1" ] || return 1
    (CDPATH= cd -- "$1" 2>/dev/null && pwd -P) || return 1
}

# read_kv <file>: parse `key=value` lines (first occurrence wins) into
# KV_<key> variables for the keys this hook reads. Values are taken verbatim
# minus surrounding double quotes and a trailing CR; nothing is expanded.
read_kv() {
    unset KV_iso KV_mode KV_checkout KV_plan KV_state KV_worktree KV_base
    local line key val
    [ -r "$1" ] || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        line=${line%$'\r'}
        case "$line" in
            iso=*|mode=*|checkout=*|plan=*|state=*|worktree=*|base=*) ;;
            *) continue ;;
        esac
        key=${line%%=*}
        val=${line#*=}
        case "$val" in
            \"*\") val=${val#\"}; val=${val%\"} ;;
        esac
        case "$key" in
            iso)      [ -n "${KV_iso+x}" ]      || KV_iso=$val ;;
            mode)     [ -n "${KV_mode+x}" ]     || KV_mode=$val ;;
            checkout) [ -n "${KV_checkout+x}" ] || KV_checkout=$val ;;
            plan)     [ -n "${KV_plan+x}" ]     || KV_plan=$val ;;
            state)    [ -n "${KV_state+x}" ]    || KV_state=$val ;;
            worktree) [ -n "${KV_worktree+x}" ] || KV_worktree=$val ;;
            base)     [ -n "${KV_base+x}" ]     || KV_base=$val ;;
        esac
    done < "$1"
    return 0
}

# sanitize <value>: the echo boundary. Empty stays empty (the field is then
# omitted); otherwise the value must be <= 256 characters and match the pinned
# charset, else the literal token `withheld` is printed in its place.
sanitize() {
    local v=$1
    [ -n "$v" ] || { printf ''; return 0; }
    if [ "${#v}" -gt 256 ]; then
        printf 'withheld'; return 0
    fi
    case "$v" in
        *[!A-Za-z0-9_./:@+-]*) printf 'withheld' ;;
        *) printf '%s' "$v" ;;
    esac
}

hook_main "$@"
exit 0
