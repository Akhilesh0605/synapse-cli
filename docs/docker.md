┌─────────────────────────────────────────┐
│           YOUR MACHINE (HOST)           │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │      Docker Container             │  │
│  │      (sandbox)                    │  │
│  │                                   │  │
│  │  rm -rf /    → deletes nothing    │  │
│  │  on host                          │  │
│  │                                   │  │
│  │  pip install → installs inside    │  │
│  │  container only                   │  │
│  │                                   │  │
│  │  curl evil.com → BLOCKED          │  │
│  │  (--network=none)                 │  │
│  │                                   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Your files: SAFE                       │
│  Your OS: SAFE                          │
│  Your network: SAFE                     │
└─────────────────────────────────────────┘