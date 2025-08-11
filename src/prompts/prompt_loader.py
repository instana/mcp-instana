import importlib
import json
import logging
import os

# Configure logger for this module
logger = logging.getLogger(__name__)


def load_prompts_from_config(path):
    with open(path, "r") as f:
        return json.load(f)

# Register prompts from the configuration file
def register_prompts(server, config_path=None):
    if config_path is None:
        current_dir = os.path.dirname(__file__)
        config_path = os.path.join(current_dir, "prompt_registry.json")

    # Load prompts from the JSON configuration file
    prompts = load_prompts_from_config(config_path)

    for prompt in prompts:
        try:
            module = importlib.import_module(prompt["module"])
            function = getattr(module, prompt["function"])
            server.tool(name=prompt["name"], description=prompt["description"])(function)
        except Exception as e:
            logger.error(f"Failed to load {prompt['name']}: {e}", exc_info=True)
