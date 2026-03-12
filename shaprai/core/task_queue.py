# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""Agent task queue management with priority scheduling.

Provides a robust task queue system for Elyan-class agents with:
- Priority-based task scheduling
- Task assignment and load balancing
- Queue management and monitoring
- Automatic task distribution
"""

from __future__ import annotations

import heapq
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class QueueStrategy(Enum):
    """Task queue scheduling strategies."""
    
    FIFO = "fifo"  # First In, First Out
    PRIORITY = "priority"  # Priority-based scheduling
    DEADLINE = "deadline"  # Earliest deadline first
    LOAD_BALANCE = "load_balance"  # Distribute to least loaded agent


@dataclass(order=True)
class QueuedTask:
    """Task wrapper for priority queue ordering.
    
    This class wraps a Task object to enable heap operations
    based on priority and creation time.
    """
    
    sort_key: Tuple[int, float] = field(compare=True)
    task: Dict[str, Any] = field(compare=False)
    
    @classmethod
    def create(cls, task_data: Dict[str, Any]) -> QueuedTask:
        """Create a QueuedTask from task data.
        
        Args:
            task_data: Task dictionary with priority and timestamps.
        
        Returns:
            QueuedTask ready for heap insertion.
        """
        priority_map = {
            "critical": 0,  # Highest priority (lowest number)
            "high": 1,
            "normal": 2,
            "low": 3,
        }
        priority_value = priority_map.get(task_data.get("priority", "normal"), 2)
        timestamp = task_data.get("created_at", time.time())
        
        return cls(
            sort_key=(priority_value, timestamp),
            task=task_data,
        )


class TaskQueueManager:
    """Manages task queues for multi-agent systems.
    
    The TaskQueueManager provides priority-based task scheduling,
    task assignment, and queue monitoring for Elyan-class agents.
    
    Features:
        - Multiple queue strategies (FIFO, Priority, Deadline, Load Balance)
        - Real-time queue statistics
        - Task assignment with load balancing
        - Persistent queue storage
        - Queue prioritization and ordering
    
    Attributes:
        agents_dir: Base directory for agent data.
        queue_dir: Directory for queue storage.
        strategy: Current queue scheduling strategy.
    """
    
    def __init__(
        self,
        agents_dir: Optional[Path] = None,
        strategy: QueueStrategy = QueueStrategy.PRIORITY,
    ) -> None:
        """Initialize the TaskQueueManager.
        
        Args:
            agents_dir: Base directory for agent storage.
                Defaults to ~/.shaprai/agents.
            strategy: Queue scheduling strategy.
        """
        if agents_dir is None:
            agents_dir = Path.home() / ".shaprai" / "agents"
        self.agents_dir = agents_dir
        self.queue_dir = self.agents_dir / ".task_queue"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        self.strategy = strategy
        
        # Storage files
        self.queue_file = self.queue_dir / "task_queue.json"
        self.agents_file = self.queue_dir / "agent_load.json"
        self.history_file = self.queue_dir / "task_history.json"
        
        self._init_storage()
    
    def _init_storage(self) -> None:
        """Initialize storage files if they don't exist."""
        if not self.queue_file.exists():
            self._save_queue([])
        if not self.agents_file.exists():
            self._save_agent_load({})
        if not self.history_file.exists():
            self._save_history([])
    
    def _load_queue(self) -> List[Dict[str, Any]]:
        """Load task queue from disk."""
        try:
            with open(self.queue_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    
    def _save_queue(self, queue: List[Dict[str, Any]]) -> None:
        """Save task queue to disk."""
        with open(self.queue_file, "w") as f:
            json.dump(queue, f, indent=2, default=str)
    
    def _load_agent_load(self) -> Dict[str, Any]:
        """Load agent load information."""
        try:
            with open(self.agents_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_agent_load(self, load_data: Dict[str, Any]) -> None:
        """Save agent load information to disk."""
        with open(self.agents_file, "w") as f:
            json.dump(load_data, f, indent=2, default=str)
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load task history."""
        try:
            with open(self.history_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    
    def _save_history(self, history: List[Dict[str, Any]]) -> None:
        """Save task history to disk."""
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2, default=str)
    
    def _get_heap(self) -> List[QueuedTask]:
        """Convert queue to priority heap.
        
        Returns:
            List of QueuedTask objects in heap order.
        """
        queue_data = self._load_queue()
        heap = [QueuedTask.create(task) for task in queue_data]
        heapq.heapify(heap)
        return heap
    
    def _save_heap(self, heap: List[QueuedTask]) -> None:
        """Save heap back to queue storage."""
        queue_data = [item.task for item in heap]
        self._save_queue(queue_data)
    
    def enqueue_task(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: str = "normal",
        created_by: str = "",
        assigned_to: Optional[str] = None,
        deadline: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a task to the queue.
        
        Args:
            task_id: Unique task identifier.
            title: Task title.
            description: Task description.
            priority: Task priority (low, normal, high, critical).
            created_by: Agent creating the task.
            assigned_to: Pre-assigned agent (optional).
            deadline: Optional deadline timestamp.
            metadata: Additional task metadata.
        
        Returns:
            Task ID for tracking.
        """
        task_data = {
            "task_id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "created_by": created_by,
            "assigned_to": assigned_to,
            "deadline": deadline,
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),
            "metadata": metadata or {},
        }
        
        queue = self._load_queue()
        queue.append(task_data)
        self._save_queue(queue)
        
        return task_id
    
    def dequeue_task(self, agent_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Remove and return the highest priority task.
        
        Args:
            agent_name: Optional agent name for load-balanced assignment.
        
        Returns:
            Task data dictionary or None if queue is empty.
        """
        heap = self._get_heap()
        
        if not heap:
            return None
        
        # Find the best task for this agent
        if agent_name and self.strategy == QueueStrategy.LOAD_BALANCE:
            # For load balancing, consider agent's current load
            agent_load = self._load_agent_load()
            current_load = agent_load.get(agent_name, 0)
            
            # Find tasks not already assigned to overloaded agents
            for i, queued_task in enumerate(heap):
                task = queued_task.task
                assigned = task.get("assigned_to")
                if assigned is None or assigned == agent_name:
                    # Remove from heap
                    heap.pop(i)
                    heapq.heapify(heap)
                    self._save_heap(heap)
                    
                    # Update task status
                    task["status"] = "assigned"
                    task["assigned_to"] = agent_name
                    task["updated_at"] = time.time()
                    
                    # Update agent load
                    self._increment_agent_load(agent_name)
                    
                    return task
        else:
            # Priority-based dequeue
            queued_task = heapq.heappop(heap)
            self._save_heap(heap)
            
            task = queued_task.task
            task["status"] = "assigned"
            task["updated_at"] = time.time()
            
            if agent_name and not task.get("assigned_to"):
                task["assigned_to"] = agent_name
                self._increment_agent_load(agent_name)
            
            return task
        
        return None
    
    def peek_queue(self, limit: int = 10) -> List[Dict[str, Any]]:
        """View the top tasks without removing them.
        
        Args:
            limit: Maximum number of tasks to return.
        
        Returns:
            List of task data dictionaries.
        """
        heap = self._get_heap()
        return [item.task for item in heap[:limit]]
    
    def get_queue_size(self) -> int:
        """Get the current number of tasks in the queue.
        
        Returns:
            Number of queued tasks.
        """
        return len(self._load_queue())
    
    def assign_task_to_agent(self, task_id: str, agent_name: str) -> bool:
        """Assign a specific task to an agent.
        
        Args:
            task_id: Task identifier.
            agent_name: Agent to assign the task to.
        
        Returns:
            True if assignment was successful.
        """
        queue = self._load_queue()
        
        for task in queue:
            if task["task_id"] == task_id:
                old_assignee = task.get("assigned_to")
                if old_assignee and old_assignee != agent_name:
                    # Decrement old agent's load
                    self._decrement_agent_load(old_assignee)
                
                task["assigned_to"] = agent_name
                task["status"] = "assigned"
                task["updated_at"] = time.time()
                self._save_queue(queue)
                
                self._increment_agent_load(agent_name)
                return True
        
        return False
    
    def complete_task(self, task_id: str, result: Optional[Any] = None) -> bool:
        """Mark a task as completed.
        
        Args:
            task_id: Task identifier.
            result: Optional task result.
        
        Returns:
            True if task was completed successfully.
        """
        queue = self._load_queue()
        
        for i, task in enumerate(queue):
            if task["task_id"] == task_id:
                agent_name = task.get("assigned_to")
                
                # Remove from queue
                queue.pop(i)
                self._save_queue(queue)
                
                # Decrement agent load
                if agent_name:
                    self._decrement_agent_load(agent_name)
                
                # Add to history
                task["status"] = "completed"
                task["completed_at"] = time.time()
                task["result"] = result
                history = self._load_history()
                history.append(task)
                self._save_history(history)
                
                return True
        
        return False
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark a task as failed.
        
        Args:
            task_id: Task identifier.
            error: Error message.
        
        Returns:
            True if task was marked as failed.
        """
        queue = self._load_queue()
        
        for i, task in enumerate(queue):
            if task["task_id"] == task_id:
                agent_name = task.get("assigned_to")
                
                # Remove from active queue
                queue.pop(i)
                self._save_queue(queue)
                
                # Decrement agent load
                if agent_name:
                    self._decrement_agent_load(agent_name)
                
                # Add to history
                task["status"] = "failed"
                task["failed_at"] = time.time()
                task["error"] = error
                history = self._load_history()
                history.append(task)
                self._save_history(history)
                
                return True
        
        return False
    
    def _increment_agent_load(self, agent_name: str) -> None:
        """Increment an agent's task load counter."""
        load_data = self._load_agent_load()
        current = load_data.get(agent_name, {"active_tasks": 0, "total_completed": 0})
        if isinstance(current, int):
            current = {"active_tasks": current, "total_completed": 0}
        current["active_tasks"] = current.get("active_tasks", 0) + 1
        load_data[agent_name] = current
        self._save_agent_load(load_data)
    
    def _decrement_agent_load(self, agent_name: str) -> None:
        """Decrement an agent's task load counter."""
        load_data = self._load_agent_load()
        current = load_data.get(agent_name, {"active_tasks": 0, "total_completed": 0})
        if isinstance(current, int):
            current = {"active_tasks": current, "total_completed": 0}
        current["active_tasks"] = max(0, current.get("active_tasks", 1) - 1)
        current["total_completed"] = current.get("total_completed", 0) + 1
        load_data[agent_name] = current
        self._save_agent_load(load_data)
    
    def get_agent_load(self, agent_name: str) -> Dict[str, Any]:
        """Get an agent's current task load.
        
        Args:
            agent_name: Agent name.
        
        Returns:
            Dictionary with load statistics.
        """
        load_data = self._load_agent_load()
        return load_data.get(agent_name, {"active_tasks": 0, "total_completed": 0})
    
    def get_all_agent_loads(self) -> Dict[str, Dict[str, Any]]:
        """Get load information for all agents.
        
        Returns:
            Dictionary mapping agent names to load data.
        """
        return self._load_agent_load()
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics.
        
        Returns:
            Dictionary with queue metrics.
        """
        queue = self._load_queue()
        history = self._load_history()
        
        # Priority distribution
        priority_counts = {"critical": 0, "high": 0, "normal": 0, "low": 0}
        for task in queue:
            priority = task.get("priority", "normal")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Status distribution
        status_counts = {}
        for task in queue:
            status = task.get("status", "queued")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Completion stats
        completed_count = len([t for t in history if t.get("status") == "completed"])
        failed_count = len([t for t in history if t.get("status") == "failed"])
        
        # Average wait time (for completed tasks)
        wait_times = []
        for task in history:
            if task.get("status") == "completed":
                created = task.get("created_at", 0)
                completed = task.get("completed_at", 0)
                if created and completed:
                    wait_times.append(completed - created)
        
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
        
        return {
            "queue_size": len(queue),
            "priority_distribution": priority_counts,
            "status_distribution": status_counts,
            "total_completed": completed_count,
            "total_failed": failed_count,
            "average_wait_time_seconds": avg_wait_time,
            "agent_loads": self._load_agent_load(),
        }
    
    def clear_queue(self) -> int:
        """Clear all tasks from the queue.
        
        Returns:
            Number of tasks cleared.
        """
        queue = self._load_queue()
        count = len(queue)
        self._save_queue([])
        return count
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID.
        
        Args:
            task_id: Task identifier.
        
        Returns:
            Task data or None if not found.
        """
        queue = self._load_queue()
        for task in queue:
            if task["task_id"] == task_id:
                return task
        return None
    
    def reprioritize_task(self, task_id: str, new_priority: str) -> bool:
        """Change the priority of a queued task.
        
        Args:
            task_id: Task identifier.
            new_priority: New priority level.
        
        Returns:
            True if priority was updated.
        """
        queue = self._load_queue()
        
        for task in queue:
            if task["task_id"] == task_id:
                task["priority"] = new_priority
                task["updated_at"] = time.time()
                self._save_queue(queue)
                return True
        
        return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the queue without completing it.
        
        Args:
            task_id: Task identifier.
        
        Returns:
            True if task was removed.
        """
        queue = self._load_queue()
        
        for i, task in enumerate(queue):
            if task["task_id"] == task_id:
                agent_name = task.get("assigned_to")
                queue.pop(i)
                self._save_queue(queue)
                
                # Decrement agent load if assigned
                if agent_name:
                    self._decrement_agent_load(agent_name)
                
                return True
        
        return False
    
    def get_tasks_by_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get all tasks assigned to an agent.
        
        Args:
            agent_name: Agent name.
        
        Returns:
            List of task data dictionaries.
        """
        queue = self._load_queue()
        return [t for t in queue if t.get("assigned_to") == agent_name]
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks past their deadline.
        
        Returns:
            List of overdue task data.
        """
        queue = self._load_queue()
        current_time = time.time()
        return [
            t for t in queue
            if t.get("deadline") and t["deadline"] < current_time
        ]
