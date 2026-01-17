if [[ "${ENABLE_SIGNAL:-false}" == "true" ]]; then
    AGENT_PID=$(pgrep -u "$user" -f "asus-user-agent" | head -n 1)

    if [[ -n "$AGENT_PID" ]]; then
        kill -SIGUSR1 "$AGENT_PID"
        exit 0
    fi
fi
