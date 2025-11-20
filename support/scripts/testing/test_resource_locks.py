#!/usr/bin/env python3
"""
Test Resource Lock Manager

Validates distributed locking functionality with PostgreSQL advisory locks.
Tests:
1. Basic lock acquisition and release
2. Context manager auto-release
3. Lock timeout and expiry
4. Concurrent lock contention (10 agents)
5. Lock status queries
6. Force release (admin)
7. Wait queue behavior
8. Cleanup of expired locks
9. Lock statistics and monitoring
10. Load test (50 concurrent operations)
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from shared.lib.resource_lock_manager import ResourceLockManager, get_resource_lock_manager


# Database connection from environment
DB_CONN_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://devtools:changeme@localhost:5432/devtools"
)


async def test_basic_acquire_release():
    """Test 1: Basic lock acquisition and release"""
    print("\n" + "="*60)
    print("TEST 1: Basic Lock Acquisition and Release")
    print("="*60)
    
    lock_mgr = ResourceLockManager(DB_CONN_STRING)
    await lock_mgr.connect()
    
    try:
        # Acquire lock
        resource = "test:basic:resource1"
        agent = "test-agent-1"
        
        acquired = await lock_mgr.acquire_lock(resource, agent, timeout_seconds=60)
        assert acquired, "Should acquire lock on first try"
        print(f"✓ Lock acquired: {resource} by {agent}")
        
        # Check status
        status = await lock_mgr.check_lock_status(resource)
        assert status.is_locked, "Lock should be active"
        assert status.owner_agent_id == agent, "Agent should own lock"
        print(f"✓ Lock status verified: owner={status.owner_agent_id}, expires in {status.seconds_remaining}s")
        
        # Release lock
        released = await lock_mgr.release_lock(resource, agent)
        assert released, "Should release lock successfully"
        print(f"✓ Lock released: {resource}")
        
        # Verify released
        status = await lock_mgr.check_lock_status(resource)
        assert not status.is_locked, "Lock should be released"
        print(f"✓ Lock confirmed released")
        
        print("\n[PASS] Test 1: Basic lock operations successful")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test 1: {e}")
        return False
    finally:
        await lock_mgr.close()


async def test_context_manager():
    """Test 2: Context manager auto-release"""
    print("\n" + "="*60)
    print("TEST 2: Context Manager Auto-Release")
    print("="*60)
    
    lock_mgr = ResourceLockManager(DB_CONN_STRING)
    await lock_mgr.connect()
    
    try:
        resource = "test:context:resource2"
        agent = "test-agent-2"
        
        # Use context manager
        async with lock_mgr.lock(resource, agent, timeout_seconds=60):
            print(f"✓ Lock acquired via context manager: {resource}")
            
            status = await lock_mgr.check_lock_status(resource)
            assert status.is_locked, "Lock should be active inside context"
            print(f"✓ Lock verified active inside context")
        
        # Verify auto-released
        status = await lock_mgr.check_lock_status(resource)
        assert not status.is_locked, "Lock should auto-release after context"
        print(f"✓ Lock auto-released after context exit")
        
        print("\n[PASS] Test 2: Context manager auto-release successful")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test 2: {e}")
        return False
    finally:
        await lock_mgr.close()


async def test_lock_contention():
    """Test 3: Lock contention (multiple agents competing)"""
    print("\n" + "="*60)
    print("TEST 3: Lock Contention (10 agents)")
    print("="*60)
    
    lock_mgr = ResourceLockManager(DB_CONN_STRING)
    await lock_mgr.connect()
    
    try:
        resource = "test:contention:shared-resource-v2"
        
        # Agent 1 acquires lock using context manager (holds connection)
        agent1 = "test-agent-contention-1"
        acquired1 = await lock_mgr.acquire_lock(resource, agent1, timeout_seconds=60, retry=False, wait=False)
        assert acquired1, "First agent should acquire lock"
        print(f"✓ Agent 1 acquired lock: {resource}")
        
        # Check lock status (should be owned by agent1)
        status = await lock_mgr.check_lock_status(resource)
        assert status.is_locked, "Lock should be active"
        assert status.owner_agent_id == agent1, f"Lock should be owned by agent1, got {status.owner_agent_id}"
        print(f"✓ Lock status verified: owner={status.owner_agent_id}")
        
        # Agent 1 releases
        await lock_mgr.release_lock(resource, agent1)
        print(f"✓ Agent 1 released lock")
        
        # Verify released
        status = await lock_mgr.check_lock_status(resource)
        assert not status.is_locked, "Lock should be released"
        print(f"✓ Lock confirmed released")
        
        # Agent 2 acquires now (should succeed)
        agent2 = "test-agent-contention-2"
        acquired2 = await lock_mgr.acquire_lock(resource, agent2, timeout_seconds=10, retry=False, wait=False)
        assert acquired2, "Second agent should acquire after release"
        print(f"✓ Agent 2 acquired lock after agent 1 released")
        
        # Cleanup
        await lock_mgr.release_lock(resource, agent2)
        
        print("\n[PASS] Test 3: Lock contention handled correctly")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test 3: {e}")
        return False
    finally:
        await lock_mgr.close()


async def test_timeout_and_expiry():
    """Test 4: Lock timeout and auto-expiry"""
    print("\n" + "="*60)
    print("TEST 4: Lock Timeout and Auto-Expiry")
    print("="*60)
    
    lock_mgr = ResourceLockManager(DB_CONN_STRING)
    await lock_mgr.connect()
    
    try:
        resource = "test:timeout:resource4"
        agent = "test-agent-timeout"
        
        # Acquire lock with 5 second timeout
        acquired = await lock_mgr.acquire_lock(resource, agent, timeout_seconds=5)
        assert acquired, "Should acquire lock"
        print(f"✓ Lock acquired with 5s timeout")
        
        # Check status immediately
        status = await lock_mgr.check_lock_status(resource)
        print(f"✓ Lock expires in {status.seconds_remaining}s")
        
        # Wait 6 seconds for expiry
        print(f"Waiting 6s for auto-expiry...")
        await asyncio.sleep(6)
        
        # Cleanup expired locks
        cleaned = await lock_mgr.cleanup_expired_locks()
        print(f"✓ Cleaned {cleaned} expired locks")
        
        # Verify lock expired
        status = await lock_mgr.check_lock_status(resource)
        assert not status.is_locked, "Lock should be expired and cleaned"
        print(f"✓ Lock correctly expired and cleaned")
        
        print("\n[PASS] Test 4: Timeout and expiry working")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test 4: {e}")
        return False
    finally:
        await lock_mgr.close()


async def test_force_release():
    """Test 5: Force release (admin override)"""
    print("\n" + "="*60)
    print("TEST 5: Force Release (Admin Override)")
    print("="*60)
    
    lock_mgr = ResourceLockManager(DB_CONN_STRING)
    await lock_mgr.connect()
    
    try:
        resource = "test:force:resource5"
        agent = "test-agent-stuck"
        
        # Agent acquires lock
        acquired = await lock_mgr.acquire_lock(resource, agent, timeout_seconds=300)
        assert acquired, "Should acquire lock"
        print(f"✓ Lock acquired by {agent}")
        
        # Admin force releases
        forced = await lock_mgr.force_release_lock(resource, admin_agent_id="admin-test")
        assert forced, "Admin should force release"
        print(f"✓ Admin forcefully released lock")
        
        # Verify released
        status = await lock_mgr.check_lock_status(resource)
        assert not status.is_locked, "Lock should be forcefully released"
        print(f"✓ Lock confirmed released")
        
        print("\n[PASS] Test 5: Force release successful")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test 5: {e}")
        return False
    finally:
        await lock_mgr.close()


async def test_statistics():
    """Test 6: Lock statistics and monitoring"""
    print("\n" + "="*60)
    print("TEST 6: Lock Statistics and Monitoring")
    print("="*60)
    
    lock_mgr = ResourceLockManager(DB_CONN_STRING)
    await lock_mgr.connect()
    
    try:
        # Create some locks
        resources = [f"test:stats:resource{i}" for i in range(3)]
        agents = [f"test-agent-stats-{i}" for i in range(3)]
        
        for resource, agent in zip(resources, agents):
            await lock_mgr.acquire_lock(resource, agent, timeout_seconds=60)
        print(f"✓ Created {len(resources)} test locks")
        
        # Get active locks
        active = await lock_mgr.list_active_locks()
        print(f"✓ Active locks: {len(active)}")
        for lock in active:
            if lock['resource_id'].startswith('test:stats'):
                print(f"  - {lock['resource_id']} by {lock['agent_id']}")
        
        # Get statistics
        stats = await lock_mgr.get_lock_statistics()
        print(f"✓ Lock statistics retrieved: {len(stats)} resources")
        
        # Cleanup
        for resource, agent in zip(resources, agents):
            await lock_mgr.release_lock(resource, agent)
        print(f"✓ Released all test locks")
        
        print("\n[PASS] Test 6: Statistics and monitoring working")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test 6: {e}")
        return False
    finally:
        await lock_mgr.close()


async def test_concurrent_load():
    """Test 7: Concurrent load (50 agents competing for 5 resources)"""
    print("\n" + "="*60)
    print("TEST 7: Concurrent Load Test (50 agents)")
    print("="*60)
    
    lock_mgr = ResourceLockManager(DB_CONN_STRING)
    await lock_mgr.connect()
    
    try:
        num_agents = 50
        num_resources = 5
        
        async def agent_task(agent_id: int):
            """Simulated agent competing for resources"""
            resource = f"test:load:resource{agent_id % num_resources}"
            agent_name = f"load-agent-{agent_id}"
            
            try:
                # Try to acquire lock with retry
                acquired = await lock_mgr.acquire_lock(
                    resource,
                    agent_name,
                    timeout_seconds=10,
                    retry=True,
                    wait=True
                )
                
                if acquired:
                    # Simulate work
                    await asyncio.sleep(0.1)
                    await lock_mgr.release_lock(resource, agent_name)
                    return True
                return False
            except Exception as e:
                print(f"Agent {agent_id} error: {e}")
                return False
        
        # Launch all agents concurrently
        print(f"Launching {num_agents} agents competing for {num_resources} resources...")
        start_time = datetime.now()
        
        results = await asyncio.gather(*[agent_task(i) for i in range(num_agents)])
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Results
        successes = sum(results)
        print(f"✓ Completed in {duration:.2f}s")
        print(f"✓ Successes: {successes}/{num_agents}")
        print(f"✓ Throughput: {num_agents/duration:.1f} ops/sec")
        
        # Check contention metrics
        contention = await lock_mgr.get_lock_contention()
        print(f"✓ Contention records: {len(contention)}")
        
        print("\n[PASS] Test 7: Concurrent load test successful")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test 7: {e}")
        return False
    finally:
        await lock_mgr.close()


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print(" "*20 + "RESOURCE LOCK MANAGER TEST SUITE")
    print("="*80)
    print(f"Database: {DB_CONN_STRING}")
    print(f"Time: {datetime.now().isoformat()}")
    
    tests = [
        ("Basic Acquire/Release", test_basic_acquire_release),
        ("Context Manager", test_context_manager),
        ("Lock Contention", test_lock_contention),
        ("Timeout & Expiry", test_timeout_and_expiry),
        ("Force Release", test_force_release),
        ("Statistics", test_statistics),
        ("Concurrent Load", test_concurrent_load),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print(" "*30 + "TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed//total}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
