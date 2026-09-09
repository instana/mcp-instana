"""Prompts package for MCP Instana."""

# Global registry for all prompts
PROMPT_REGISTRY = []

def auto_register_prompt(func):
    """Store raw function; MCP registration is deferred to server startup."""
    PROMPT_REGISTRY.append(func)
    return func
