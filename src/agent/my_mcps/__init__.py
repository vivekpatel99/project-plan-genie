import json
import os
import re
from pathlib import Path

from loguru import logger

mcp_config_file = Path(__file__).parent / "mcp_config.json"
if mcp_config_file.exists() is False:
    msg = f"MCP config file not found at {mcp_config_file}"
    logger.error(msg)
    raise FileNotFoundError(msg)


with mcp_config_file.open(mode="r", encoding="utf-8") as f:
    _mcp_config = json.load(f)


def resolve_env_vars(config: dict):
    for server, server_config in config["mcpServers"].items():
        if "env" in server_config:
            for env_var in server_config["env"]:
                config["mcpServers"][server]["env"][env_var] = os.environ.get(env_var, "")
                if config["mcpServers"][server]["env"][env_var] == "":
                    msg = f"Environment variable {env_var} is not set"
                    raise ValueError(msg)
        if "args" in server_config:
            for i, arg in enumerate(server_config["args"]):
                # Handle ${VAR} patterns anywhere in the string
                def replace_env_var(match):
                    env_var = match.group(1)
                    env_value = os.environ.get(env_var, "")
                    if env_value == "":
                        msg = f"Environment variable {env_var} is not set"
                        raise ValueError(msg)
                    return env_value

                # Replace all ${VAR} patterns in the string
                config["mcpServers"][server]["args"][i] = re.sub(r"\$\{([^}]+)\}", replace_env_var, arg)
    return config


mcp_config = resolve_env_vars(config=_mcp_config)
