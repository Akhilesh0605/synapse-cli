# SynapseCLI SQLite Database Layer - Summary

## FILES 

| File | Purpose |
|------|---------|
| [app/database/__init__.py](app/database/__init__.py) | Package exports for database module |
| [app/database/connection.py](app/database/connection.py) | SQLAlchemy engine, session factory, DB initialization |
| [app/database/models.py](app/database/models.py) | 3 ORM models: CommandHistory, PipelineTrace, BehavioralMemory |
| [app/database/repository.py](app/database/repository.py) | CRUD operations: save/read command history, query by ID |
| [app/database/memory.py](app/database/memory.py) | Behavioral memory: intent tracking, memory context injection |
| [tests/test_database_layer.py](tests/test_database_layer.py) | End-to-end database verification tests |

## HOW IT WORKS

The database layer implements a 3-table system that tracks every command execution in the 7-stage pipeline:

1. **CommandHistory** - Records each user query, intent classification, executed command, and result (success/blocked/error)
2. **PipelineTrace** - Tracks latency and success/failure for each of the 7 pipeline stages
3. **BehavioralMemory** - Learns user intent patterns and frequency to enhance future LLM decisions

**Data Flow:**
- User query → LLM#1 gets injected with top 5 recent intents from BehavioralMemory
- Pipeline executes 7 stages (intent generation, policy, shell synthesis, validation, execution policy, execution, trace)
- After execution, `save_command_history()` persists the full response + all stage traces
- If execution succeeds, `update_memory()` increments the intent's use_count (behavioral learning)

## INTEGRATION POINTS

### 1. Database Initialization
**File:** [app/cli/main.py](app/cli/main.py)
```python
from app.database.connection import create_tables
create_tables()  # Called on app startup
```

### 2. Memory Context Injection (LLM #1)
**File:** [app/core/orchestrator.py](app/core/orchestrator.py)
```python
memory_context = get_memory_context()
if memory_context:
    enriched_query = f"[MEMORY: {json.dumps(memory_context)}]\n{user_query}"
```

### 3. Save Command History (Every Pipeline)
**File:** [app/core/orchestrator.py](app/core/orchestrator.py) - `_response()` function
```python
save_command_history(response)  # Auto-saves with request_id
```

### 4. Update Behavioral Memory (Successful Executions Only)
**File:** [app/core/orchestrator.py](app/core/orchestrator.py) - `_response()` function
```python
if status == "success":
    update_memory(intent, shell_type, command)  # Increments use_count
```

## DATABASE SCHEMA

### CommandHistory Table
```sql
CREATE TABLE command_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id VARCHAR UNIQUE NOT NULL,
  query TEXT NOT NULL,
  intent VARCHAR,
  action_type VARCHAR,
  shell_type VARCHAR,
  command TEXT,
  risk_level VARCHAR,
  status VARCHAR,  -- success/blocked/error/clarify/require_confirmation
  execution_time_ms INTEGER,
  stdout TEXT,
  stderr TEXT,
  return_code INTEGER,
  created_at DATETIME DEFAULT NOW
);
CREATE INDEX idx_cmd_hist_request_id ON command_history(request_id);
Create INDEX idx_cmd_hist_created_at ON command_history(created_at);
```

### PipelineTrace Table
```sql
CREATE TABLE pipeline_trace (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id VARCHAR NOT NULL,
  stage_name VARCHAR NOT NULL,
  stage_order INTEGER,
  latency_ms INTEGER,
  success BOOLEAN,
  error_message TEXT,
  created_at DATETIME DEFAULT NOW,
  FOREIGN KEY (request_id) REFERENCES command_history(request_id)
);
CREATE INDEX idx_pipeline_trace_request_id ON pipeline_trace(request_id);
CREATE INDEX idx_pipeline_trace_created_at ON pipeline_trace(created_at);
```

### BehavioralMemory Table
```sql
CREATE TABLE behavioral_memory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  intent VARCHAR UNIQUE NOT NULL,
  shell_type VARCHAR,
  top_command TEXT,
  use_count INTEGER DEFAULT 1,
  last_used_at DATETIME DEFAULT NOW
);
CREATE INDEX idx_behav_mem_intent ON behavioral_memory(intent);
```

## SQL VERIFICATION QUERIES

### View Recent Commands
```sql
SELECT request_id, query, status, created_at FROM command_history 
ORDER BY created_at DESC LIMIT 5;
```

### View Top Intents by Usage
```sql
SELECT intent, use_count, shell_type, last_used_at FROM behavioral_memory 
ORDER BY use_count DESC;
```

### View Pipeline Stages for a Specific Request
```sql
SELECT stage_name, stage_order, latency_ms, success FROM pipeline_trace 
WHERE request_id = '<REQUEST_ID>' ORDER BY stage_order;
```

### View Command Success Rate
```sql
SELECT status, COUNT(*) as count FROM command_history 
GROUP BY status;
```

### View Total Pipeline Latency Distribution
```sql
SELECT 
  query,
  (SELECT SUM(latency_ms) FROM pipeline_trace WHERE request_id = ch.request_id) as total_latency_ms
FROM command_history ch
ORDER BY total_latency_ms DESC
LIMIT 10;
```

### Find Slow Stages
```sql
SELECT stage_name, AVG(latency_ms) as avg_latency_ms, COUNT(*) as count
FROM pipeline_trace
GROUP BY stage_name
ORDER BY avg_latency_ms DESC;
```

## VERIFY IN PYTHON

### Test 1: Insert and Retrieve Command History
```python
from app.database.repository import save_command_history, get_recent_commands

response = {
    "request_id": "test-123",
    "query": "open settings",
    "intent": "open_settings",
    "status": "success",
    "command": 'Start-Process "ms-settings:"',
    "pipeline_stages": [
        {"name": "intent_generation", "latency_ms": 45, "success": True},
        {"name": "execution", "latency_ms": 234, "success": True},
    ]
}

save_command_history(response)
recent = get_recent_commands(limit=5)
print(f"Saved and retrieved {len(recent)} commands")
```

### Test 2: Update and Retrieve Memory
```python
from app.database.memory import update_memory, get_memory_context

# Learn intent pattern
update_memory("open_youtube", "powershell", "Start-Process https://www.youtube.com")
update_memory("open_youtube", "powershell", "Start-Process https://www.youtube.com")
update_memory("open_youtube", "powershell", "Start-Process https://www.youtube.com")

# Get memory context for LLM injection
context = get_memory_context()
print(f"Top intents: {context['top_intents']}")
print(f"LLM will receive: [MEMORY: {context}]")
```

### Test 3: Run Full Test Suite
```bash
cd c:\Users\Akhil\Desktop\SynapseCLI
.\synapsecli\Scripts\python.exe tests/test_database_layer.py
```

## DATABASE LOCATION

**SQLite File:** `C:\Users\Akhil\Desktop\SynapseCLI\synapsecli.db`

**Browse with SQLite CLI:**
```powershell
sqlite3 synapsecli.db
sqlite> .tables
sqlite> SELECT * FROM command_history;
sqlite> .quit
```

## KEY FEATURES

✓ **No Crashes:** All DB operations wrapped in try/except - DB failures never crash the pipeline
✓ **Graceful Degradation:** If DB unavailable, pipeline still runs (memory context injection optional)
✓ **Automatic Upsert:** Behavioral memory auto-increments use_count on repeated intents
✓ **Request Tracking:** Every command has unique request_id for full trace audit
✓ **Stage Latency:** Each 7-stage trace recorded for performance analysis
✓ **Foreign Keys:** PipelineTrace links to CommandHistory via request_id
✓ **Indexed Queries:** Fast lookups on request_id and created_at timestamps
✓ **Type Safe:** SQLAlchemy ORM with Pydantic serialization

## TEST RESULTS

All 4 test suites passing:

```
✓ PASS: Database Creation
✓ PASS: Command History
✓ PASS: Behavioral Memory
✓ PASS: Pipeline Traces

Total: 4/4 tests passed
```

**Live Test:** Pipeline execution with database integration completed successfully:
- Query: "decrease screen brightness by 3%"
- Status: ✓ success
- Duration: 2434ms
- Data Saved: ✓ CommandHistory, ✓ BehavioralMemory, ✓ PipelineTrace

## NEXT STEPS

1. **Analytics Dashboard:** Build a dashboard using the query results to visualize pipeline performance
2. **Memory Optimization:** Implement archival to keep `behavioral_memory` lean (top N intents only)
3. **Error Reporting:** Build alerts when error/blocked commands exceed thresholds
4. **LLM Feedback Loop:** Use `top_commands` in system prompt to prioritize frequently-used patterns
5. **Export/Backup:** Implement daily SQLite export for audit compliance
