#!/usr/bin/env python
"""Test script to verify SQLite database layer is working."""
import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import create_tables, get_db, DB_PATH
from app.database.models import CommandHistory, PipelineTrace, BehavioralMemory
from app.database.repository import (
    save_command_history,
    get_recent_commands,
    get_command_by_request_id,
)
from app.database.memory import update_memory, get_memory_context


def test_database_creation():
    """Test that tables are created."""
    print("[*] Testing database creation...")
    create_tables()
    if os.path.exists(DB_PATH):
        print(f"✓ Database file created at: {DB_PATH}")
    else:
        print(f"✗ Database file not found at: {DB_PATH}")
        return False
    return True


def test_command_history():
    """Test saving and retrieving command history."""
    print("\n[*] Testing CommandHistory...")
    
    # Create test response
    test_response = {
        "request_id": "test-cmd-001",
        "query": "open youtube",
        "intent": "open_youtube",
        "action_type": "web_navigation",
        "shell_type": "powershell",
        "command": "Start-Process https://www.youtube.com",
        "risk_level": "low",
        "status": "success",
        "execution_time_ms": 523,
        "stdout": "Browser opened",
        "stderr": "",
        "return_code": 0,
        "pipeline_stages": [
            {"name": "intent_generation", "latency_ms": 45, "success": True},
            {"name": "policy_evaluation", "latency_ms": 12, "success": True},
            {"name": "execution", "latency_ms": 466, "success": True},
        ]
    }
    
    # Save
    save_command_history(test_response)
    print("✓ Saved test command history")
    
    # Retrieve recent
    recent = get_recent_commands(limit=5)
    if recent:
        print(f"✓ Retrieved {len(recent)} recent commands")
    
    # Retrieve by ID
    cmd = get_command_by_request_id("test-cmd-001")
    if cmd and cmd.get("query") == "open youtube":
        print("✓ Retrieved command by request_id")
    else:
        print("✗ Failed to retrieve by request_id")
        return False
    
    return True


def test_behavioral_memory():
    """Test behavioral memory operations."""
    print("\n[*] Testing BehavioralMemory...")
    
    # Add some memory records
    test_intents = [
        ("open_youtube", "powershell", "Start-Process https://www.youtube.com"),
        ("open_settings", "powershell", 'Start-Process "ms-settings:"'),
        ("increase_volume", "powershell", "Get-Volume | Set-Volume -Level 5"),
        ("decrease_screen_brightness", "powershell", "powercfg -setdcvalueindex"),
        ("open_chrome", "powershell", "Start-Process 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'"),
    ]
    
    for intent, shell, command in test_intents:
        update_memory(intent, shell, command)
    
    print("✓ Inserted 5 test intent records")
    
    # Get memory context
    context = get_memory_context()
    if context:
        print(f"✓ Retrieved memory context:")
        print(f"  - Top intents: {context.get('top_intents', [])}")
        print(f"  - Top shells: {context.get('top_shells', [])}")
        print(f"  - Top commands count: {len(context.get('top_commands', []))}")
    else:
        print("✗ No memory context returned")
        return False
    
    # Update same intent multiple times (should increment)
    for i in range(3):
        update_memory("open_youtube", "powershell", "Start-Process https://www.youtube.com")
    
    print("✓ Updated open_youtube 3 times (testing increment)")
    
    # Check updated use_count
    context2 = get_memory_context()
    youtube_intent = context2.get("top_intents", [])[0] if context2 else None
    if youtube_intent == "open_youtube":
        print("✓ open_youtube now top due to use_count increment")
    
    return True


def test_pipeline_traces():
    """Test PipelineTrace records."""
    print("\n[*] Testing PipelineTrace...")
    
    # Create a response with multiple stages
    test_response = {
        "request_id": "test-trace-001",
        "query": "decrease screen brightness by 5%",
        "intent": "decrease_screen_brightness",
        "status": "success",
        "pipeline_stages": [
            {"name": "intent_generation", "stage_order": 1, "latency_ms": 52, "success": True},
            {"name": "policy_evaluation", "stage_order": 2, "latency_ms": 10, "success": True},
            {"name": "execution", "stage_order": 3, "latency_ms": 234, "success": True},
        ]
    }
    
    save_command_history(test_response)
    print("✓ Saved response with 3 pipeline stages")
    
    # Verify traces were saved
    with get_db() as session:
        traces = session.query(PipelineTrace).filter_by(request_id="test-trace-001").all()
        if len(traces) == 3:
            print(f"✓ Retrieved {len(traces)} pipeline traces")
            for trace in traces:
                print(f"  - {trace.stage_name}: {trace.latency_ms}ms")
        else:
            print(f"✗ Expected 3 traces, got {len(traces)}")
            return False
    
    return True


def print_sql_verification_queries():
    """Print SQL queries for manual verification."""
    print("\n" + "="*60)
    print("SQL VERIFICATION QUERIES")
    print("="*60)
    
    queries = [
        ("Recent commands", "SELECT request_id, query, status, created_at FROM command_history ORDER BY created_at DESC LIMIT 5;"),
        ("Top intents by usage", "SELECT intent, use_count, shell_type, last_used_at FROM behavioral_memory ORDER BY use_count DESC;"),
        ("Pipeline stages for request", "SELECT stage_name, stage_order, latency_ms, success FROM pipeline_trace WHERE request_id = '<REQUEST_ID>' ORDER BY stage_order;"),
        ("Command success rate", "SELECT status, COUNT(*) as count FROM command_history GROUP BY status;"),
    ]
    
    for name, query in queries:
        print(f"\n{name}:")
        print(f"  {query}")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SYNAPSECLI DATABASE VERIFICATION")
    print("="*60)
    
    tests = [
        ("Database Creation", test_database_creation),
        ("Command History", test_command_history),
        ("Behavioral Memory", test_behavioral_memory),
        ("Pipeline Traces", test_pipeline_traces),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Print verification queries
    print_sql_verification_queries()
    
    print("\n" + "="*60)
    print("DATABASE LOCATION:", DB_PATH)
    print("="*60 + "\n")
    
    return all(r for _, r in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
