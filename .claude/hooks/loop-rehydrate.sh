#!/usr/bin/env bash
# loop-rehydrate.sh — the /execute-loop composer rehydrate pointer (v33.0 D7).
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
#   - OUTPUT: a CONDITIONAL pointer — a marker carries no session identity, so
#     this hook never asserts "you are the composer". Every matching run is
#     listed. Echoed values are `iso`, `mode`, `plan`, `worktree` ONLY, each
#     newline-stripped, charset-validated ([A-Za-z0-9_./:@+-]) and length-
#     capped (<= 256 characters — a non-ASCII value already fails the charset);
#     a value that fails is rendered as the literal token `withheld`.
#     Marker/journal text is DATA: it is only ever a printf argument or a
#     `cd --` operand — never eval'd, never expanded, never a command.
#   - DOCUMENTED LIMITS (fail-silent by construction): journal string values
#     may carry the contract's backslash escapes (\" \\ \n); this hook does not
#     unescape them, so such a path never realpath-matches (no pointer) and
#     would be `withheld` at the echo. A Windows-native drive path recorded in
#     a journal likewise never equals Git Bash's POSIX top-level (no pointer).
#
# No exec bit is required (invoked via `bash`).

set -u

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
    case "$common" in
        /*) ;;
        *) common="$PWD/$common" ;;
    esac
    common=$(real_dir "$common") || return 0
    base=$(dirname -- "$common")
    current_root=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
    current_root=$(real_dir "$current_root") || return 0
    loops="$base/.cursor/loops"
    [ -d "$loops" ] || return 0

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
    unset KV_iso KV_mode KV_checkout KV_plan KV_state KV_worktree
    local line key val
    [ -r "$1" ] || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        line=${line%$'\r'}
        case "$line" in
            iso=*|mode=*|checkout=*|plan=*|state=*|worktree=*) ;;
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
