function has_web_browser {
    if command -v xdg-open >/dev/null 2>&1; then  # Linux
        echo "Web browser detected in this environment"
        return 0
    elif command -v open >/dev/null 2>&1; then  # Mac
        echo "Web browser detected in this environment"
        return 0
    else
        echo "Warning: No web browser available in this environment"
        return 1
    fi
}
