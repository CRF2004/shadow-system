#!/bin/bash
# ============================================================================
# Shadow System — Shell Preexec Hook
# ============================================================================
# Source this script from your .bashrc / .zshrc to auto-track terminal
# commands as Shadow System activities.
#
# Usage:
#   echo "source $(pwd)/hooks/shell_preexec.sh" >> ~/.bashrc
#
# The hook intercepts each command before execution, categorises it, and
# POSTs an activity to the Shadow Web API.  The server must be running on
# SHADOW_HOST (default http://localhost:8080).
#
# Configuration (set before sourcing):
#   SHADOW_HOST   — Shadow Web API base URL
#   SHADOW_TOKEN  — optional Bearer token for authenticated endpoints
# ============================================================================

: "${SHADOW_HOST:=http://localhost:8080}"
SHADOW_ACTIVITIES="${SHADOW_HOST}/api/activities"

# ── Command categorisation ──────────────────────────────────────────────────

_shadow_classify() {
    local cmd="$1"

    # Normalise: collapse whitespace, lowercase
    cmd="$(echo "$cmd" | tr -s ' ' | tr '[:upper:]' '[:lower:]')"

    case "$cmd" in
        *git\ commit*|git\ commit*)
            echo "commit"
            return 0
            ;;
        *git\ push*|git\ pull*|git\ merge*|git\ rebase*)
            echo "commit"
            return 0
            ;;
        *npm\ test*|*pytest*|*go\ test*|*cargo\ test*|*jest*|*vitest*|*mocha*)
            echo "test"
            return 0
            ;;
        *npm\ run\ build*|*make*|*cargo\ build*|*go\ build*|*tsc*)
            echo "coding"
            return 0
            ;;
        *npm\ install*|*pip\ install*|*go\ get*|*cargo\ install*|*apt\ install*|*brew\ install*)
            echo "research"
            return 0
            ;;
        *git\ diff*|*git\ log*|*git\ status*|*git\ blame*)
            echo "research"
            return 0
            ;;
        *man\ *|*help\ *|*--help*)
            echo "research"
            return 0
            ;;
        *vim\ *|*nvim\ *|*code\ *|*nano\ *)
            echo "coding"
            return 0
            ;;
        *ssh\ *)
            echo "research"
            return 0
            ;;
        *docker\ *|*docker-compose\ *|*kubectl\ *)
            echo "coding"
            return 0
            ;;
        *python3\ *|*python\ *|*node\ *|*deno\ *|*bun\ *)
            # Running a script — treat as coding
            echo "coding"
            return 0
            ;;
        *curl\ *|*wget\ *|*httpie\ *)
            echo "research"
            return 0
            ;;
        *cd\ *|*ls\ *|*pwd*|*which\ *|*where\ *|*type\ *)
            # Navigation — skip, not worth tracking
            echo "skip"
            return 0
            ;;
        *echo\ *|*export\ *|*alias\ *|*unset\ *|*set\ *)
            echo "skip"
            return 0
            ;;
        *exit*|*clear*|*history*|*reset*)
            echo "skip"
            return 0
            ;;
        *&&*|||\;*)
            # Compound commands — classify by the first segment
            local first="${cmd%% &&*}"
            first="${first%%;*}"
            _shadow_classify "$first"
            return $?
            ;;
    esac

    # Fallback: if it looks like a developer command (not a pure builtin)
    if [[ "$cmd" =~ ^[a-z_-]+$ ]] && ! type "$cmd" &>/dev/null; then
        echo "coding"
    else
        echo "skip"
    fi
}

# ── Activity reporter ───────────────────────────────────────────────────────

_shadow_report_activity() {
    local action_type="$1"
    local command="$2"

    # Rate-limit: skip if we reported less than 5 s ago (debounce)
    local now
    now="$(date +%s)"
    if [[ -n "$_SHADOW_LAST_REPORT" ]] && (( now - _SHADOW_LAST_REPORT < 5 )); then
        return 0
    fi

    local payload
    payload="$(cat <<EOF
{
  "activities": [
    {
      "action": "${action_type}",
      "quantity": 1,
      "source": "shell_preexec"
    }
  ]
}
EOF
)"

    if [[ -n "$SHADOW_TOKEN" ]]; then
        curl -s -X POST "$SHADOW_ACTIVITIES" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $SHADOW_TOKEN" \
            -d "$payload" > /dev/null 2>&1 &
    else
        curl -s -X POST "$SHADOW_ACTIVITIES" \
            -H "Content-Type: application/json" \
            -d "$payload" > /dev/null 2>&1 &
    fi
    _SHADOW_LAST_REPORT="$now"
}

# ── Hook: bash (using DEBUG trap + PROMPT_COMMAND) ─────────────────────────

_shadow_preexec_bash() {
    # The last command is in BASH_COMMAND
    local cmd="$BASH_COMMAND"
    local action
    action="$(_shadow_classify "$cmd")"
    if [[ "$action" != "skip" && -n "$action" ]]; then
        _shadow_report_activity "$action" "$cmd"
    fi
}

if [[ -n "$BASH_VERSION" ]]; then
    # Use DEBUG trap — fires before each command
    trap "_shadow_preexec_bash" DEBUG
fi

# ── Hook: zsh (using preexec hook) ─────────────────────────────────────────

_shadow_preexec_zsh() {
    local cmd="$1"
    local action
    action="$(_shadow_classify "$cmd")"
    if [[ "$action" != "skip" && -n "$action" ]]; then
        _shadow_report_activity "$action" "$cmd"
    fi
}

if [[ -n "$ZSH_VERSION" ]]; then
    autoload -Uz add-zsh-hook
    add-zsh-hook preexec _shadow_preexec_zsh
fi
