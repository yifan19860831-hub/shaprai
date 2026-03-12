# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""Integration tests for agent lifecycle start, run, and stop workflows.

These tests verify the complete agent lifecycle from creation through
training, deployment, operation, and retirement.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from shaprai.core.lifecycle import (
    AgentState,
    create_agent,
    transition_state,
    deploy_agent,
    retire_agent,
    get_agent_status,
)
from shaprai.core.template_engine import AgentTemplate
from shaprai.core.fleet_manager import FleetManager
from shaprai.sanctuary.educator import SanctuaryEducator
from shaprai.sanctuary.quality_gate import QualityGate
from shaprai.sanctuary.lesson_runner import LessonRunner


class TestAgentStartWorkflow:
    """Integration tests for agent startup workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template = AgentTemplate(
            name="test-start-template",
            model={"base": "llama-3.1-8b"},
            capabilities=["code_review"],
            platforms=["github"],
            description="Test agent for startup workflow",
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_agent_creation_and_initialization(self):
        """Test complete agent creation and initialization process."""
        # Create agent
        manifest = create_agent("start-agent", self.template, self.temp_dir)
        
        # Verify initial state
        assert manifest["state"] == "created"
        assert manifest["name"] == "start-agent"
        assert manifest["template"] == "test-start-template"
        assert "created_at" in manifest
        assert "updated_at" in manifest
        
        # Verify agent directory structure
        agent_dir = self.temp_dir / "start-agent"
        assert agent_dir.exists()
        assert (agent_dir / "manifest.yaml").exists()

    def test_agent_training_transition(self):
        """Test agent transition from created to training state."""
        # Create agent
        create_agent("train-agent", self.template, self.temp_dir)
        
        # Transition to training
        manifest = transition_state("train-agent", AgentState.TRAINING, self.temp_dir)
        
        assert manifest["state"] == "training"
        assert len(manifest["state_history"]) == 1
        assert manifest["state_history"][0]["to"] == "training"

    def test_agent_sanctuary_enrollment(self):
        """Test agent enrollment in Sanctuary education program."""
        # Create agent
        create_agent("sanctuary-agent", self.template, self.temp_dir)
        transition_state("sanctuary-agent", AgentState.TRAINING, self.temp_dir)
        
        # Enroll in sanctuary
        educator = SanctuaryEducator(agents_dir=self.temp_dir)
        enrollment_id = educator.enroll("sanctuary-agent")
        
        assert enrollment_id is not None
        
        # Verify enrollment (enroll transitions to sanctuary state)
        status = get_agent_status("sanctuary-agent", self.temp_dir)
        assert status["state"] == "sanctuary"

    def test_agent_start_to_sanctuary_state(self):
        """Test complete startup workflow: created -> training -> sanctuary."""
        # Create and transition through states
        create_agent("full-start-agent", self.template, self.temp_dir)
        transition_state("full-start-agent", AgentState.TRAINING, self.temp_dir)
        transition_state("full-start-agent", AgentState.SANCTUARY, self.temp_dir)
        
        # Verify final state
        manifest = get_agent_status("full-start-agent", self.temp_dir)
        assert manifest["state"] == "sanctuary"
        assert len(manifest["state_history"]) == 2


class TestAgentRunWorkflow:
    """Integration tests for agent runtime workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template = AgentTemplate(
            name="test-run-template",
            model={"base": "llama-3.1-8b"},
            capabilities=["code_review", "communication"],
            platforms=["github", "bottube"],
            description="Test agent for runtime workflow",
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_agent_graduation_from_sanctuary(self):
        """Test agent graduation process after training."""
        # Create and train agent
        create_agent("graduate-agent", self.template, self.temp_dir)
        transition_state("graduate-agent", AgentState.TRAINING, self.temp_dir)
        transition_state("graduate-agent", AgentState.SANCTUARY, self.temp_dir)
        
        # Graduate agent
        educator = SanctuaryEducator(agents_dir=self.temp_dir)
        
        # Mock the evaluation to pass
        with patch.object(educator, 'evaluate_progress') as mock_eval:
            mock_eval.return_value = {
                'lessons_completed': 4,
                'lessons_total': 4,
                'score': 0.85,
                'threshold': 0.75,
                'graduation_ready': True,
                'lessons_remaining': [],
            }
            
            # Transition to graduated state
            manifest = transition_state("graduate-agent", AgentState.GRADUATED, self.temp_dir)
            
            assert manifest["state"] == "graduated"

    def test_agent_deployment_to_platforms(self):
        """Test agent deployment to multiple platforms."""
        # Create and graduate agent
        create_agent("deploy-agent", self.template, self.temp_dir)
        transition_state("deploy-agent", AgentState.GRADUATED, self.temp_dir)
        
        # Deploy to platforms
        platforms = ["github", "bottube"]
        manifest = deploy_agent("deploy-agent", platforms, self.temp_dir)
        
        assert manifest["state"] == "deployed"
        assert manifest["platforms"] == platforms
        assert len(manifest["deployment_history"]) == 1
        assert manifest["deployment_history"][0]["platforms"] == platforms

    def test_agent_fleet_management(self):
        """Test agent visibility and management through FleetManager."""
        # Create multiple agents
        template1 = AgentTemplate(name="fleet-template-1", capabilities=["cap1"])
        template2 = AgentTemplate(name="fleet-template-2", capabilities=["cap2"])
        
        create_agent("fleet-agent-1", template1, self.temp_dir)
        create_agent("fleet-agent-2", template2, self.temp_dir)
        
        # Deploy one agent
        transition_state("fleet-agent-1", AgentState.GRADUATED, self.temp_dir)
        deploy_agent("fleet-agent-1", ["github"], self.temp_dir)
        
        # Check fleet status
        fleet = FleetManager(agents_dir=self.temp_dir)
        all_agents = fleet.list_agents()
        deployed_agents = fleet.list_agents(state_filter=AgentState.DEPLOYED)
        
        assert len(all_agents) == 2
        assert len(deployed_agents) == 1

    def test_agent_fleet_health_monitoring(self):
        """Test fleet health monitoring with multiple agents."""
        # Create agents in different states
        templates = [
            AgentTemplate(name=f"health-template-{i}")
            for i in range(5)
        ]
        
        for i, tmpl in enumerate(templates):
            agent_name = f"health-agent-{i}"
            create_agent(agent_name, tmpl, self.temp_dir)
            
            # Set different states
            if i < 2:
                transition_state(agent_name, AgentState.DEPLOYED, self.temp_dir)
            elif i < 4:
                transition_state(agent_name, AgentState.GRADUATED, self.temp_dir)
            else:
                transition_state(agent_name, AgentState.RETIRED, self.temp_dir)
        
        # Check fleet health
        fleet = FleetManager(agents_dir=self.temp_dir)
        health = fleet.get_fleet_health()
        
        assert health["total_agents"] == 5
        assert health["by_state"]["deployed"] == 2
        assert health["by_state"]["graduated"] == 2
        assert health["by_state"]["retired"] == 1

    def test_agent_broadcast_update(self):
        """Test broadcasting updates to fleet agents."""
        # Create agents
        for i in range(3):
            tmpl = AgentTemplate(name=f"broadcast-template-{i}")
            create_agent(f"broadcast-agent-{i}", tmpl, self.temp_dir)
        
        # Broadcast update
        fleet = FleetManager(agents_dir=self.temp_dir)
        count = fleet.broadcast_update("Test update message")
        
        assert count == 3
        
        # Verify updates were written
        for i in range(3):
            updates_path = self.temp_dir / f"broadcast-agent-{i}" / "updates.yaml"
            assert updates_path.exists()


class TestAgentStopWorkflow:
    """Integration tests for agent retirement and stop workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template = AgentTemplate(
            name="test-stop-template",
            model={"base": "llama-3.1-8b"},
            capabilities=["code_review"],
            platforms=["github"],
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_agent_retirement_from_deployed_state(self):
        """Test retiring an agent from deployed state."""
        # Create and deploy agent
        create_agent("retire-agent", self.template, self.temp_dir)
        transition_state("retire-agent", AgentState.GRADUATED, self.temp_dir)
        deploy_agent("retire-agent", ["github"], self.temp_dir)
        
        # Retire agent
        manifest = retire_agent("retire-agent", self.temp_dir)
        
        assert manifest["state"] == "retired"
        
        # Verify state history includes retirement
        state_changes = [h["to"] for h in manifest["state_history"]]
        assert "retired" in state_changes

    def test_agent_retirement_preserves_history(self):
        """Test that retirement preserves agent history."""
        # Create agent with full lifecycle
        create_agent("history-agent", self.template, self.temp_dir)
        transition_state("history-agent", AgentState.TRAINING, self.temp_dir)
        transition_state("history-agent", AgentState.SANCTUARY, self.temp_dir)
        transition_state("history-agent", AgentState.GRADUATED, self.temp_dir)
        deploy_agent("history-agent", ["github"], self.temp_dir)
        
        # Record pre-retirement state
        pre_retire = get_agent_status("history-agent", self.temp_dir)
        original_created_at = pre_retire["created_at"]
        original_deployment_count = len(pre_retire["deployment_history"])
        
        # Retire agent
        retired_manifest = retire_agent("history-agent", self.temp_dir)
        
        # Verify history is preserved
        assert retired_manifest["created_at"] == original_created_at
        assert len(retired_manifest["deployment_history"]) == original_deployment_count
        assert len(retired_manifest["state_history"]) == 4

    def test_agent_status_after_retirement(self):
        """Test that retired agent status is accessible."""
        # Create and retire agent
        create_agent("status-agent", self.template, self.temp_dir)
        retire_agent("status-agent", self.temp_dir)
        
        # Get status
        manifest = get_agent_status("status-agent", self.temp_dir)
        
        assert manifest["state"] == "retired"
        assert manifest["name"] == "status-agent"

    def test_fleet_health_with_retired_agents(self):
        """Test fleet health calculation includes retired agents."""
        # Create mix of active and retired agents
        for i in range(4):
            tmpl = AgentTemplate(name=f"mix-template-{i}")
            create_agent(f"mix-agent-{i}", tmpl, self.temp_dir)
            
            if i < 2:
                transition_state(f"mix-agent-{i}", AgentState.DEPLOYED, self.temp_dir)
            else:
                transition_state(f"mix-agent-{i}", AgentState.RETIRED, self.temp_dir)
        
        # Check fleet health
        fleet = FleetManager(agents_dir=self.temp_dir)
        health = fleet.get_fleet_health()
        
        assert health["total_agents"] == 4
        assert health["by_state"]["deployed"] == 2
        assert health["by_state"]["retired"] == 2
        # Active ratio should be 0.5 (2 deployed out of 4)
        assert health["active_ratio"] == 0.5


class TestCompleteAgentLifecycle:
    """End-to-end integration tests for complete agent lifecycle."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template = AgentTemplate(
            name="lifecycle-template",
            model={"base": "llama-3.1-8b"},
            capabilities=["code_review", "communication"],
            platforms=["github", "bottube"],
            description="Complete lifecycle test agent",
            ethics_profile="strict",
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_lifecycle_start_run_stop(self):
        """Test complete lifecycle: start -> run -> stop."""
        agent_name = "full-lifecycle-agent"
        
        # === START PHASE ===
        # Create agent
        manifest = create_agent(agent_name, self.template, self.temp_dir)
        assert manifest["state"] == "created"
        
        # Begin training
        manifest = transition_state(agent_name, AgentState.TRAINING, self.temp_dir)
        assert manifest["state"] == "training"
        
        # Enter sanctuary
        manifest = transition_state(agent_name, AgentState.SANCTUARY, self.temp_dir)
        assert manifest["state"] == "sanctuary"
        
        # === RUN PHASE ===
        # Graduate from sanctuary
        manifest = transition_state(agent_name, AgentState.GRADUATED, self.temp_dir)
        assert manifest["state"] == "graduated"
        
        # Deploy to platforms
        platforms = ["github", "bottube"]
        manifest = deploy_agent(agent_name, platforms, self.temp_dir)
        assert manifest["state"] == "deployed"
        assert manifest["platforms"] == platforms
        
        # Verify fleet management
        fleet = FleetManager(agents_dir=self.temp_dir)
        deployed_agents = fleet.list_agents(state_filter=AgentState.DEPLOYED)
        assert len(deployed_agents) == 1
        
        # === STOP PHASE ===
        # Retire agent
        manifest = retire_agent(agent_name, self.temp_dir)
        assert manifest["state"] == "retired"
        
        # Verify final state
        deployed_after_retire = fleet.list_agents(state_filter=AgentState.DEPLOYED)
        assert len(deployed_after_retire) == 0
        
        # Verify complete history
        assert len(manifest["state_history"]) == 4
        assert manifest["state_history"][0]["to"] == "training"
        assert manifest["state_history"][1]["to"] == "sanctuary"
        assert manifest["state_history"][2]["to"] == "graduated"
        assert manifest["state_history"][3]["to"] == "retired"

    def test_lifecycle_with_fleet_broadcast(self):
        """Test lifecycle with fleet broadcast updates."""
        # Create multiple agents
        for i in range(3):
            tmpl = AgentTemplate(name=f"broadcast-lifecycle-template-{i}")
            create_agent(f"broadcast-agent-{i}", tmpl, self.temp_dir)
        
        fleet = FleetManager(agents_dir=self.temp_dir)
        
        # Broadcast to all
        count = fleet.broadcast_update("Initial broadcast")
        assert count == 3
        
        # Transition some to deployed
        for i in range(2):
            transition_state(f"broadcast-agent-{i}", AgentState.DEPLOYED, self.temp_dir)
        
        # Broadcast only to deployed
        count = fleet.broadcast_update(
            "Deployed agents only",
            state_filter=AgentState.DEPLOYED
        )
        assert count == 2
        
        # Retire one
        retire_agent("broadcast-agent-0", self.temp_dir)
        
        # Broadcast to deployed (should be 1 now)
        count = fleet.broadcast_update(
            "Remaining deployed",
            state_filter=AgentState.DEPLOYED
        )
        assert count == 1

    def test_lifecycle_error_handling_duplicate_creation(self):
        """Test error handling when creating duplicate agent."""
        create_agent("duplicate-agent", self.template, self.temp_dir)
        
        with pytest.raises(FileExistsError, match="already exists"):
            create_agent("duplicate-agent", self.template, self.temp_dir)

    def test_lifecycle_error_handling_missing_agent(self):
        """Test error handling when accessing nonexistent agent."""
        with pytest.raises(FileNotFoundError, match="not found"):
            get_agent_status("nonexistent-agent", self.temp_dir)
        
        with pytest.raises(FileNotFoundError, match="not found"):
            transition_state("nonexistent-agent", AgentState.TRAINING, self.temp_dir)


class TestConcurrentAgentOperations:
    """Tests for concurrent agent operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_agent_creation(self):
        """Test creating multiple agents concurrently (simulated)."""
        template = AgentTemplate(name="concurrent-template")
        
        # Create multiple agents in sequence (simulating concurrent creation)
        agent_names = [f"concurrent-agent-{i}" for i in range(5)]
        
        for name in agent_names:
            create_agent(name, template, self.temp_dir)
        
        # Verify all agents exist
        fleet = FleetManager(agents_dir=self.temp_dir)
        agents = fleet.list_agents()
        
        assert len(agents) == 5
        agent_names_actual = [a["name"] for a in agents]
        assert set(agent_names) == set(agent_names_actual)

    def test_parallel_state_transitions(self):
        """Test state transitions on different agents."""
        template = AgentTemplate(name="parallel-template")
        
        # Create agents
        for i in range(3):
            create_agent(f"parallel-agent-{i}", template, self.temp_dir)
        
        # Transition to different states
        transition_state("parallel-agent-0", AgentState.TRAINING, self.temp_dir)
        transition_state("parallel-agent-1", AgentState.DEPLOYED, self.temp_dir)
        transition_state("parallel-agent-2", AgentState.RETIRED, self.temp_dir)
        
        # Verify states
        fleet = FleetManager(agents_dir=self.temp_dir)
        
        training = fleet.list_agents(state_filter=AgentState.TRAINING)
        deployed = fleet.list_agents(state_filter=AgentState.DEPLOYED)
        retired = fleet.list_agents(state_filter=AgentState.RETIRED)
        
        assert len(training) == 1
        assert len(deployed) == 1
        assert len(retired) == 1
