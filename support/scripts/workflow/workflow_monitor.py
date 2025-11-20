#!/usr/bin/env python3
"""
Multi-Agent Workflow Monitoring Dashboard

Real-time monitoring of:
- Active workflows and their status
- Resource locks (who holds what)
- Lock contention and wait queues
- Agent activity and coordination
- Workflow performance metrics

Usage:
    python support/scripts/workflow_monitor.py
    python support/scripts/workflow_monitor.py --watch  # Auto-refresh every 5s
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from shared.lib.workflow_state import WorkflowStateManager
from shared.lib.resource_lock_manager import ResourceLockManager


# Database connection
DB_CONN_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://devtools:changeme@localhost:5432/devtools"
)


class WorkflowMonitor:
    """Real-time workflow and lock monitoring"""
    
    def __init__(self):
        self.state_mgr = WorkflowStateManager(DB_CONN_STRING)
        self.lock_mgr = ResourceLockManager(DB_CONN_STRING)
    
    async def initialize(self):
        """Initialize connections"""
        await self.state_mgr.connect()
        await self.lock_mgr.connect()
    
    async def close(self):
        """Cleanup connections"""
        await self.state_mgr.close()
        await self.lock_mgr.close()
    
    async def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows"""
        return await self.state_mgr.list_active_workflows()
    
    async def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        stats = await self.state_mgr.get_workflow_statistics()
        return stats[0] if stats else {}
    
    async def get_active_locks(self) -> List[Dict[str, Any]]:
        """Get all active resource locks"""
        return await self.lock_mgr.list_active_locks()
    
    async def get_lock_contention(self) -> List[Dict[str, Any]]:
        """Get lock contention metrics"""
        return await self.lock_mgr.get_lock_contention()
    
    async def get_wait_queue(self) -> List[Dict[str, Any]]:
        """Get agents waiting for locks"""
        return await self.lock_mgr.get_wait_queue()
    
    def render_dashboard(
        self,
        workflows: List[Dict[str, Any]],
        workflow_stats: Dict[str, Any],
        locks: List[Dict[str, Any]],
        contention: List[Dict[str, Any]],
        wait_queue: List[Dict[str, Any]]
    ):
        """Render monitoring dashboard"""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Header
        print("=" * 100)
        print(" " * 30 + "MULTI-AGENT WORKFLOW MONITOR")
        print("=" * 100)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Workflow Statistics
        print("━" * 100)
        print("WORKFLOW STATISTICS")
        print("━" * 100)
        if workflow_stats:
            print(f"Total Workflows:     {workflow_stats.get('total_workflows', 0)}")
            print(f"Active:              {workflow_stats.get('active_workflows', 0)}")
            print(f"Completed:           {workflow_stats.get('completed_workflows', 0)}")
            print(f"Failed:              {workflow_stats.get('failed_workflows', 0)}")
            print(f"Avg Duration:        {workflow_stats.get('avg_duration_seconds', 0):.2f}s")
        else:
            print("No workflow statistics available")
        print()
        
        # Active Workflows
        print("━" * 100)
        print("ACTIVE WORKFLOWS")
        print("━" * 100)
        if workflows:
            print(f"{'Workflow ID':<35} {'Type':<20} {'Status':<12} {'Duration':<10} {'Agents':<15}")
            print("-" * 100)
            for wf in workflows:
                # Handle both dict and Pydantic model
                if hasattr(wf, 'workflow_id'):
                    workflow_id = wf.workflow_id[:34]
                    workflow_type = wf.workflow_type[:19]
                    status = wf.status[:11]
                    created = wf.started_at
                    agents = wf.participating_agents if hasattr(wf, 'participating_agents') else []
                else:
                    workflow_id = wf['workflow_id'][:34]
                    workflow_type = wf['workflow_type'][:19]
                    status = wf['status'][:11]
                    created = wf.get('started_at', wf.get('created_at'))
                    agents = wf.get('participating_agents', [])
                
                # Calculate duration
                if isinstance(created, str):
                    from dateutil.parser import parse
                    created = parse(created)
                duration = (datetime.now() - created.replace(tzinfo=None)).total_seconds()
                duration_str = f"{duration:.1f}s"
                
                # Parse agents
                if isinstance(agents, str):
                    import json
                    agents = json.loads(agents)
                agents_str = f"{len(agents)} agents"[:14]
                
                print(f"{workflow_id:<35} {workflow_type:<20} {status:<12} {duration_str:<10} {agents_str:<15}")
        else:
            print("No active workflows")
        print()
        
        # Active Locks
        print("━" * 100)
        print("ACTIVE RESOURCE LOCKS")
        print("━" * 100)
        if locks:
            print(f"{'Resource':<40} {'Owner':<25} {'Acquired':<20} {'Expires In':<12}")
            print("-" * 100)
            for lock in locks:
                resource = lock['resource_id'][:39]
                owner = lock['agent_id'][:24]
                
                acquired = lock['acquired_at']
                if isinstance(acquired, str):
                    from dateutil.parser import parse
                    acquired = parse(acquired)
                acquired_str = acquired.strftime('%H:%M:%S')
                
                expires = lock['expires_at']
                if isinstance(expires, str):
                    from dateutil.parser import parse
                    expires = parse(expires)
                remaining = (expires.replace(tzinfo=None) - datetime.now()).total_seconds()
                expires_str = f"{int(remaining)}s" if remaining > 0 else "EXPIRED"
                
                print(f"{resource:<40} {owner:<25} {acquired_str:<20} {expires_str:<12}")
        else:
            print("No active locks")
        print()
        
        # Lock Contention
        print("━" * 100)
        print("LOCK CONTENTION")
        print("━" * 100)
        if contention:
            print(f"{'Resource':<45} {'Total Requests':<18} {'Avg Wait (ms)':<15} {'Max Wait (ms)':<15}")
            print("-" * 100)
            for item in contention[:10]:  # Top 10 most contended
                resource = item['resource_id'][:44]
                total = item['total_requests']
                avg_wait = item.get('avg_wait_time_ms', 0) or 0
                max_wait = item.get('max_wait_time_ms', 0) or 0
                
                print(f"{resource:<45} {total:<18} {avg_wait:<15.0f} {max_wait:<15.0f}")
        else:
            print("No lock contention")
        print()
        
        # Wait Queue
        print("━" * 100)
        print("AGENTS WAITING FOR LOCKS")
        print("━" * 100)
        if wait_queue:
            print(f"{'Agent':<30} {'Resource':<40} {'Wait Time':<15} {'Priority':<10}")
            print("-" * 100)
            for item in wait_queue:
                agent = item['agent_id'][:29]
                resource = item['resource_id'][:39]
                
                requested = item['requested_at']
                if isinstance(requested, str):
                    from dateutil.parser import parse
                    requested = parse(requested)
                wait_time = (datetime.now() - requested.replace(tzinfo=None)).total_seconds()
                wait_str = f"{wait_time:.1f}s"
                
                priority = item.get('priority', 5)
                
                print(f"{agent:<30} {resource:<40} {wait_str:<15} {priority:<10}")
        else:
            print("No agents waiting")
        print()
        
        print("=" * 100)
        print("Press Ctrl+C to exit")
        print("=" * 100)
    
    async def run_once(self):
        """Run monitoring dashboard once"""
        try:
            # Gather all data in parallel
            workflows, workflow_stats, locks, contention, wait_queue = await asyncio.gather(
                self.get_active_workflows(),
                self.get_workflow_stats(),
                self.get_active_locks(),
                self.get_lock_contention(),
                self.get_wait_queue()
            )
            
            # Render dashboard
            self.render_dashboard(workflows, workflow_stats, locks, contention, wait_queue)
            
        except Exception as e:
            print(f"Error collecting monitoring data: {e}")
    
    async def run_watch(self, interval: int = 5):
        """Run monitoring dashboard with auto-refresh"""
        try:
            while True:
                await self.run_once()
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Multi-Agent Workflow Monitor")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh every 5 seconds")
    parser.add_argument("--interval", type=int, default=5, help="Refresh interval (seconds)")
    
    args = parser.parse_args()
    
    monitor = WorkflowMonitor()
    
    try:
        await monitor.initialize()
        
        if args.watch:
            print(f"Starting monitoring dashboard (refresh every {args.interval}s)...")
            print("Press Ctrl+C to exit\n")
            await asyncio.sleep(1)
            await monitor.run_watch(args.interval)
        else:
            await monitor.run_once()
        
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        return 1
    finally:
        await monitor.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
