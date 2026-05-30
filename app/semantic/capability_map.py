# capability_map.py
COMMAND_CAPABILITIES = {
    # filesystem read
    "get-childitem":  "filesystem.read",
    "dir":            "filesystem.read",
    "ls":             "filesystem.read",
    "get-location":   "filesystem.read",
    "pwd":            "filesystem.read",
    "get-item":       "filesystem.read",
    "get-content":    "filesystem.read",
    "cat":            "filesystem.read",
    "type":           "filesystem.read",
    "find":           "filesystem.read",
    "grep":           "filesystem.read",
    "select-string":  "filesystem.read",
    "test-path":      "filesystem.read",

    # filesystem write
    "new-item":       "filesystem.write",
    "mkdir":          "filesystem.write",
    "copy-item":      "filesystem.write",
    "move-item":      "filesystem.write",
    "cp":             "filesystem.write",
    "mv":             "filesystem.write",

    # process read
    "get-process":    "process.read",
    "ps":             "process.read",
    "tasklist":       "process.read",
    "whoami":         "process.read",
    "get-service":    "process.read",

    # process write
    "stop-process":   "process.write",
    "kill":           "process.write",
    "taskkill":       "process.write",

    # network read
    "ping":           "network.read",
    "ipconfig":       "network.read",
    "ifconfig":       "network.read",
    "netstat":        "network.read",
    "nslookup":       "network.read",
    "curl":           "network.read",
    "wget":           "network.read",
    "ip":             "network.read",

    # runtime info
    "python":         "runtime.info",
    "python3":        "runtime.info",
    "pip":            "runtime.write",
    "pip3":           "runtime.write",
    "node":           "runtime.info",
    "npm":            "runtime.write",

    # git
    "git":            "vcs.read",

    # docker
    "docker":         "container.read",
    # docker (powershell)
    "get-container": "container.read",

    # system info
    "echo":           "system.info",
    "date":           "system.info",
    "uname":          "system.info",
    "hostname":       "system.info",
    "get-date":       "system.info",
    "get-host":       "system.info",
    "get-command":    "system.info",
    "get-psdrive":    "system.info",
    "df":             "system.info",
    "du":             "system.info",
    "get-computerinfo":"system.info",  #
    "systeminfo":       "system.info",    
    "get-wmiobject":    "system.info",

    # process launch (powershell)
    "start-process": "system.launch",
    "start":         "system.launch",
    "open":          "system.launch",
    "explorer":      "system.launch",
}