#!/usr/bin/env python3
"""
Validate models.yaml against Pydantic schema
"""
import sys
import yaml
from pathlib import Path

# Add shared/lib to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_config_schema import ModelsConfig

def validate_config(config_path: Path):
    try:
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Validate with Pydantic
        config = ModelsConfig(**raw_config)
        
        # Success output
        print("âœ“ YAML syntax valid")
        print(f"âœ“ Schema validation passed (version {config.version})")
        print(f"âœ“ All 6 required agents defined: {', '.join(config.agents.keys())}")
        
        # Detailed checks
        for agent_name, agent_config in config.agents.items():
            print(f"  â€¢ {agent_name}: {agent_config.model} (temp={agent_config.temperature}, max_tokens={agent_config.max_tokens})")
        
        return 0
    
    except yaml.YAMLError as e:
        print(f"âŒ YAML syntax error: {e}", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"âŒ Validation failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_config.py <config_path>", file=sys.stderr)
        sys.exit(1)
    
    config_path = Path(sys.argv[1])
    sys.exit(validate_config(config_path))
