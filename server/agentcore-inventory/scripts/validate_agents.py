#!/usr/bin/env python3
# =============================================================================
# Agent Structure Validation Script
# Validates all 14 agents follow the correct AgentCore pattern
# =============================================================================

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Expected agents
EXPECTED_AGENTS = [
    "carrier",
    "compliance",
    "equipment_research",
    "estoque_control",
    "expedition",
    "import",
    "intake",
    "learning",
    "nexo_import",
    "observation",
    "reconciliacao",
    "reverse",
    "schema_evolution",
    "validation",
]

# Required files for each agent
REQUIRED_FILES = [
    "__init__.py",
    "agent.py",
    "main.py",
    "Dockerfile",
    "requirements.txt",
]

# Required in tools directory
REQUIRED_TOOLS = [
    "__init__.py",
]


def validate_agent_structure(agents_dir: Path) -> Tuple[bool, List[str]]:
    """Validate all agents have the correct structure."""
    errors = []

    for agent_name in EXPECTED_AGENTS:
        agent_dir = agents_dir / agent_name

        # Check agent directory exists
        if not agent_dir.exists():
            errors.append(f"❌ Missing agent directory: {agent_name}")
            continue

        # Check required files
        for file_name in REQUIRED_FILES:
            file_path = agent_dir / file_name
            if not file_path.exists():
                errors.append(f"❌ {agent_name}: Missing {file_name}")

        # Check tools directory
        tools_dir = agent_dir / "tools"
        if not tools_dir.exists():
            errors.append(f"❌ {agent_name}: Missing tools/ directory")
        else:
            # Check tools __init__.py
            tools_init = tools_dir / "__init__.py"
            if not tools_init.exists():
                errors.append(f"❌ {agent_name}: Missing tools/__init__.py")

            # Check at least one tool file exists
            tool_files = [f for f in tools_dir.glob("*.py") if f.name != "__init__.py"]
            if not tool_files:
                errors.append(f"⚠️  {agent_name}: No tool files in tools/")

    return len(errors) == 0, errors


def validate_shared_module(base_dir: Path) -> Tuple[bool, List[str]]:
    """Validate shared module exists with required files."""
    errors = []
    shared_dir = base_dir / "shared"

    if not shared_dir.exists():
        errors.append("❌ Missing shared/ directory")
        return False, errors

    required_shared = [
        "__init__.py",
        "audit_emitter.py",
        "a2a_client.py",
        "xray_tracer.py",
    ]

    for file_name in required_shared:
        file_path = shared_dir / file_name
        if not file_path.exists():
            errors.append(f"❌ shared/: Missing {file_name}")

    return len(errors) == 0, errors


def validate_dockerfile_content(agents_dir: Path) -> Tuple[bool, List[str]]:
    """Validate Dockerfiles have correct settings."""
    errors = []

    for agent_name in EXPECTED_AGENTS:
        dockerfile = agents_dir / agent_name / "Dockerfile"
        if not dockerfile.exists():
            continue

        content = dockerfile.read_text()

        # Check ARM64 platform
        if "linux/arm64" not in content:
            errors.append(f"⚠️  {agent_name}: Dockerfile missing ARM64 platform")

        # Check Python 3.13
        if "python:3.13" not in content:
            errors.append(f"⚠️  {agent_name}: Dockerfile not using Python 3.13")

        # Check port 9000
        if "9000" not in content:
            errors.append(f"⚠️  {agent_name}: Dockerfile not exposing port 9000")

    return len(errors) == 0, errors


def validate_agent_id(agents_dir: Path) -> Tuple[bool, List[str]]:
    """Validate each agent has correct AGENT_ID."""
    errors = []

    for agent_name in EXPECTED_AGENTS:
        agent_file = agents_dir / agent_name / "agent.py"
        if not agent_file.exists():
            continue

        content = agent_file.read_text()

        # Check AGENT_ID is defined
        if "AGENT_ID" not in content:
            errors.append(f"⚠️  {agent_name}: agent.py missing AGENT_ID")

        # Check AGENT_NAME is defined
        if "AGENT_NAME" not in content:
            errors.append(f"⚠️  {agent_name}: agent.py missing AGENT_NAME")

        # Check create_*_agent function exists
        if "def create_" not in content:
            errors.append(f"⚠️  {agent_name}: agent.py missing create_*_agent function")

    return len(errors) == 0, errors


def main():
    """Run all validations."""
    print("=" * 60)
    print("🔍 Agent Structure Validation")
    print("=" * 60)
    print()

    # Determine paths
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    agents_dir = base_dir / "agents"

    all_valid = True
    all_errors = []

    # 1. Validate agent structure
    print("📁 Checking agent directory structure...")
    valid, errors = validate_agent_structure(agents_dir)
    all_valid = all_valid and valid
    all_errors.extend(errors)
    print(f"   {'✅ All agents present' if valid else '❌ Issues found'}")

    # 2. Validate shared module
    print("📦 Checking shared module...")
    valid, errors = validate_shared_module(base_dir)
    all_valid = all_valid and valid
    all_errors.extend(errors)
    print(f"   {'✅ Shared module complete' if valid else '❌ Issues found'}")

    # 3. Validate Dockerfiles
    print("🐳 Checking Dockerfiles...")
    valid, errors = validate_dockerfile_content(agents_dir)
    all_valid = all_valid and valid
    all_errors.extend(errors)
    print(f"   {'✅ Dockerfiles valid' if valid else '⚠️  Warnings found'}")

    # 4. Validate agent.py content
    print("🤖 Checking agent definitions...")
    valid, errors = validate_agent_id(agents_dir)
    all_valid = all_valid and valid
    all_errors.extend(errors)
    print(f"   {'✅ Agent definitions valid' if valid else '⚠️  Warnings found'}")

    print()
    print("=" * 60)

    if all_errors:
        print("📋 Issues Found:")
        for error in all_errors:
            print(f"   {error}")
        print()

    if all_valid:
        print("✅ All validations passed!")
        print(f"   {len(EXPECTED_AGENTS)} agents ready for deployment")
        return 0
    else:
        print(f"⚠️  Validation completed with {len(all_errors)} issue(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
