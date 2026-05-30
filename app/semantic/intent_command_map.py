# intent_command_map.py
INTENT_ALLOWED_COMMANDS = {
    # filesystem read
    "list_files":               {"get-childitem", "dir", "ls"},
    "list_current_directory":   {"get-childitem", "dir", "ls", "get-location", "pwd"},
    "show_current_directory":   {"get-location", "pwd", "get-childitem", "dir"},
    "find_files":               {"get-childitem", "find", "dir"},
    "read_file":                {"get-content", "cat", "type"},
    "search_file_content":      {"select-string", "grep", "find"},
    "check_path_exists":        {"test-path", "ls", "dir"},

    # filesystem write
    "create_directory":         {"new-item", "mkdir"},
    "create_file":              {"new-item"},
    "copy_file":                {"copy-item", "cp"},
    "move_file":                {"move-item", "mv"},

    # process / user
    "show_current_user":        {"whoami"},
    "show_running_processes":   {"get-process", "ps", "tasklist"},
    "show_services":            {"get-service"},
    "stop_process":             {"stop-process", "kill", "taskkill"},

    # network
    "ping_host":                {"ping"},
    "show_network_info":        {"ipconfig", "ifconfig", "netstat"},
    "dns_lookup":               {"nslookup"},
    "check_ip_address":         {"ipconfig", "ifconfig", "ip"},
    "show_network_info":        {"ipconfig", "ifconfig", "netstat", "ip"},

    # runtime
    "show_python_version":      {"python", "python3"},
    "install_python_package":   {"pip", "pip3"},
    "show_node_version":        {"node"},
    "install_node_package":     {"npm"},

    # git
    "git_status":               {"git"},
    "git_log":                  {"git"},
    "git_clone":                {"git"},

    # docker
    "list_docker_containers":   {"docker"},
    "docker_status":            {"docker"},

    # system info
    "show_disk_usage":          {"df", "du", "get-psdrive"},
    "show_system_info":         {"uname", "get-host", "hostname"},
    "show_date":                {"date", "get-date"},
    "echo_message":             {"echo"},

    "show_system_info": {
        "get-host",
        "get-computerinfo", 
        "hostname",
        "uname",
        "systeminfo",          
        "get-wmiobject",       
    },

    "open_application": {"start", "open", "explorer"},


    # browser/application launch
    "open_chrome": {"start"},
    # application launch
    "open_ollama_app": {"start-process"},
}