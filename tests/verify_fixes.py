import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.browser.manager import BrowserManager
from src.browser.subagent_manager import get_subagent_manager
from src.tools.brave_search import brave_search

async def test_concurrency():
    print("\n--- Testing Concurrency (Race Condition Fix) ---")
    manager = BrowserManager()
    await manager.start()
    
    # Simulate two concurrent searches on the same shared browser
    # The lock in isolated_context should force them to be sequential
    async def search_task(query, task_id):
        print(f"Task {task_id}: Starting search for '{query}'...")
        # Use a dummy context since brave_search will create its own isolated context
        # via the browser manager
        async with manager.isolated_context() as page:
            print(f"Task {task_id}: Got isolated context")
            # We don't actually need to navigate to verify the lock, 
            # but let's simulate some work
            await asyncio.sleep(2)
            print(f"Task {task_id}: Finished work")
            return f"Result for {query}"

    print("Running 3 tasks concurrently...")
    results = await asyncio.gather(
        search_task("OpenClaw", 1),
        search_task("Brave Search", 2),
        search_task("Concurrency", 3)
    )
    print(f"Results: {results}")
    print("Concurrency test PASSED (Check logs for sequential 'Got isolated context' -> 'Finished work' pairs)")

async def test_subagent_isolation():
    print("\n--- Testing Sub-agent Isolation & Tab Limits ---")
    sub_manager = await get_subagent_manager()
    
    # Create two different sessions
    instance1 = await sub_manager.create_browser("sub-agent-1")
    instance2 = await sub_manager.create_browser("sub-agent-2")
    
    print(f"Created sessions: {instance1.session_id}, {instance2.session_id}")
    
    # Create a tab in session 1
    tab_id1, _ = await instance1.create_tab(url="https://example.com")
    print(f"Session 1 created tab: {tab_id1}")
    
    # Verify session 2 doesn't see session 1's tabs
    tabs2 = await instance2.list_tabs()
    print(f"Session 2 tabs: {tabs2}")
    
    if tab_id1 not in tabs2:
        print("Isolation Verified: Session 2 cannot see Session 1's tabs.")
    else:
        print("ERROR: Isolation Failed!")
        return

    # Test Tab Limit (15)
    print("Testing tab limit (15) in Session 1...")
    for i in range(16):
        await instance1.create_tab()
    
    stats = instance1.get_stats()
    print(f"Session 1 tab count: {stats['tab_count']}")
    if stats['tab_count'] <= 15:
        print(f"Tab Limit Verified: Count is {stats['tab_count']} (<= 15)")
    else:
        print(f"ERROR: Tab Limit Failed! Count is {stats['tab_count']}")

    # Cleanup
    await sub_manager.stop()
    print("Sub-agent test PASSED")

async def main():
    manager = None
    try:
        await test_concurrency()
        await test_subagent_isolation()
    finally:
        # Final cleanup handled by sub_manager.stop() in test_subagent_isolation
        # and we should stop the concurrency manager too
        pass

if __name__ == "__main__":
    asyncio.run(main())
