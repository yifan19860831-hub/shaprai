# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""Agent lifecycle management.

Manages the state machine for Elyan-class agents from creation through
deployment and eventual retirement.

Lifecycle: CREATED -> TRAINING -> SANCTUARY -> GRADUATED -> DEPLOYED -> RETIRED
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from shaprai.core.template_engine import AgentTemplate


class AgentState(Enum):
    """Agent lifecycle states.
    
    Each agent progresses through these states in order:
    CREATED → TRAINING → SANCTUARY → GRADUATED → DEPLOYED → RETIRED
    
    States represent major milestones in an agent's development and deployment.
    Transitions are tracked in the manifest's state_history for audit purposes.
    """

    CREATED = "created"  # Initial state after agent creation from template
    TRAINING = "training"  # Undergoing SFT, DPO, and DriftLock training phases
    SANCTUARY = "sanctuary"  # Education program for PR etiquette and ethics
    DEPLOYED = "deployed"  # Actively running on one or more platforms
    GRADUATED = "graduated"  # Completed Sanctuary, ready for deployment
    RETIRED = "retired"  # Terminal state, agent is no longer active


def create_agent(
    name: str,
    template: AgentTemplate,
    agents_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create a new agent from a template.

    Creates the agent directory, writes the manifest, and sets the initial
    state to CREATED.

    Args:
        name: Unique agent identifier.
        template: AgentTemplate defining the agent's configuration.
        agents_dir: Base directory for agent storage. Defaults to ~/.shaprai/agents.

    Returns:
        Dictionary with the agent's initial manifest.

    Raises:
        FileExistsError: If an agent with this name already exists.
    """
    if agents_dir is None:
        agents_dir = Path.home() / ".shaprai" / "agents"

    agent_dir = agents_dir / name
    if agent_dir.exists():
        raise FileExistsError(f"Agent '{name}' already exists at {agent_dir}")

    agent_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": name,
        "state": AgentState.CREATED.value,
        "template": template.name,
        "model": template.model,
        "personality": template.personality,
        "capabilities": template.capabilities,
        "platforms": template.platforms,
        "ethics_profile": template.ethics_profile,
        "driftlock": template.driftlock,
        "rtc_config": template.rtc_config,
        "created_at": time.time(),
        "updated_at": time.time(),
        "training_history": [],
        "deployment_history": [],
    }

    manifest_path = agent_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    return manifest


def _load_manifest(name: str, agents_dir: Path) -> Dict[str, Any]:
    """Load an agent's manifest from disk.
    
    Internal helper function used by all lifecycle operations.
    Reads the YAML manifest file and returns it as a dictionary.
    
    Args:
        name: Agent identifier (also the subdirectory name).
        agents_dir: Base directory containing agent subdirectories.
    
    Returns:
        Parsed manifest dictionary with all agent metadata.
    
    Raises:
        FileNotFoundError: If the agent directory or manifest doesn't exist.
    
    Example:
        >>> agents_dir = Path.home() / ".shaprai" / "agents"
        >>> manifest = _load_manifest("bounty-hunter-01", agents_dir)
        >>> print(manifest["state"])
        'deployed'
    """
    manifest_path = agents_dir / name / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Agent '{name}' not found at {agents_dir / name}")
    with open(manifest_path, "r") as f:
        return yaml.safe_load(f)


def _save_manifest(name: str, manifest: Dict[str, Any], agents_dir: Path) -> None:
    """Save an agent's manifest to disk.
    
    Internal helper function that persists manifest changes.
    Automatically updates the 'updated_at' timestamp before writing.
    
    Args:
        name: Agent identifier.
        manifest: Manifest dictionary to serialize and save.
        agents_dir: Base directory containing agent subdirectories.
    
    Side Effects:
        - Updates manifest['updated_at'] to current timestamp
        - Overwrites existing manifest.yaml file
    
    Note:
        Uses YAML format with preserved key order (sort_keys=False)
        for human-readable output.
    """
    manifest["updated_at"] = time.time()
    manifest_path = agents_dir / name / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)


def transition_state(
    name: str,
    new_state: AgentState,
    agents_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Transition an agent to a new lifecycle state.
    
    Core state machine function that moves an agent between lifecycle states.
    Records the transition in state_history for audit and analytics.
    
    Valid state transitions (enforced by convention, not code):
        CREATED → TRAINING → SANCTUARY → GRADUATED → DEPLOYED → RETIRED
    
    Args:
        name: Unique agent identifier.
        new_state: Target AgentState enum value.
        agents_dir: Base directory for agent storage. 
            Defaults to ~/.shaprai/agents if not provided.
    
    Returns:
        Updated manifest dictionary with new state and transition record.
    
    Side Effects:
        - Updates manifest['state'] to new_state.value
        - Appends transition record to manifest['state_history']
        - Updates manifest['updated_at'] timestamp
        - Writes changes to disk
    
    Example:
        >>> manifest = transition_state("agent-001", AgentState.TRAINING)
        >>> print(manifest["state"])
        'training'
        >>> print(len(manifest["state_history"]))
        1
    """
    if agents_dir is None:
        agents_dir = Path.home() / ".shaprai" / "agents"

    manifest = _load_manifest(name, agents_dir)
    old_state = manifest["state"]
    manifest["state"] = new_state.value
    manifest.setdefault("state_history", []).append({
        "from": old_state,
        "to": new_state.value,
        "timestamp": time.time(),
    })
    _save_manifest(name, manifest, agents_dir)
    return manifest


def deploy_agent(
    name: str,
    platforms: List[str],
    agents_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Deploy an agent to the specified platforms.
    
    Marks an agent as deployed and records which platforms it's running on.
    An agent can be deployed to multiple platforms simultaneously.
    
    Supported platforms:
        - github: GitHub PR reviews, issue comments, bounty hunting
        - bottube: AI video content creation and engagement
        - moltbook: Social media interactions
        - discord: Community support and moderation
        - telegram: Messaging and notifications
    
    Args:
        name: Unique agent identifier.
        platforms: List of platform names to deploy to.
            Example: ["github", "bottube"]
        agents_dir: Base directory for agent storage.
            Defaults to ~/.shaprai/agents if not provided.
    
    Returns:
        Updated manifest with deployment record and new state.
    
    Side Effects:
        - Sets manifest['state'] to 'deployed'
        - Updates manifest['platforms'] to provided list
        - Appends deployment record to manifest['deployment_history']
        - Writes changes to disk
    
    Example:
        >>> manifest = deploy_agent("bounty-hunter-01", ["github", "bottube"])
        >>> print(manifest["platforms"])
        ['github', 'bottube']
        >>> print(manifest["state"])
        'deployed'
    """
    if agents_dir is None:
        agents_dir = Path.home() / ".shaprai" / "agents"

    manifest = _load_manifest(name, agents_dir)
    manifest["state"] = AgentState.DEPLOYED.value
    manifest["platforms"] = platforms
    manifest.setdefault("deployment_history", []).append({
        "platforms": platforms,
        "timestamp": time.time(),
    })
    _save_manifest(name, manifest, agents_dir)
    return manifest


def retire_agent(
    name: str,
    agents_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retire an agent, removing it from active duty.
    
    Moves an agent to the RETIRED terminal state. Retired agents
    are no longer active on any platform but their history is
    preserved for reference and analytics.
    
    Common reasons for retirement:
        - Agent has completed its mission/objectives
        - Agent is being replaced by a newer version
        - Resource optimization (reducing active agent count)
        - Ethical concerns or behavioral issues
    
    Args:
        name: Unique agent identifier.
        agents_dir: Base directory for agent storage.
            Defaults to ~/.shaprai/agents if not provided.
    
    Returns:
        Updated manifest with state set to 'retired'.
    
    Note:
        Retirement is a terminal state - agents cannot be
        un-retired. Create a new agent if needed.
    
    Example:
        >>> manifest = retire_agent("old-agent-001")
        >>> print(manifest["state"])
        'retired'
    """
    return transition_state(name, AgentState.RETIRED, agents_dir)


def get_agent_status(
    name: str,
    agents_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Get the current status of an agent.
    
    Reads and returns the agent's manifest without modification.
    Useful for checking agent state, configuration, and history.
    
    Args:
        name: Unique agent identifier.
        agents_dir: Base directory for agent storage.
            Defaults to ~/.shaprai/agents if not provided.
    
    Returns:
        Complete manifest dictionary containing:
        - name: Agent identifier
        - state: Current lifecycle state
        - template: Template name used for creation
        - model: Model configuration
        - personality: Personality traits
        - capabilities: List of capabilities
        - platforms: Deployed platforms
        - ethics_profile: Ethics framework
        - driftlock: DriftLock configuration
        - created_at: Creation timestamp
        - updated_at: Last update timestamp
        - state_history: List of state transitions
        - deployment_history: List of deployments
        - training_history: List of training phases (if any)
    
    Raises:
        FileNotFoundError: If the agent doesn't exist.
    
    Example:
        >>> status = get_agent_status("bounty-hunter-01")
        >>> print(f"State: {status['state']}")
        State: deployed
        >>> print(f"Platforms: {status['platforms']}")
        Platforms: ['github', 'bottube']
    """
    if agents_dir is None:
        agents_dir = Path.home() / ".shaprai" / "agents"
    return _load_manifest(name, agents_dir)
