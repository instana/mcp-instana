"""Prompts package for MCP Instana."""
import logging

from fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Instana MCP Server")

# Global registry for all prompts
PROMPT_REGISTRY = []

def auto_register_prompt(func):
    """Wrap MCP's @mcp.prompt to also store prompt in a registry."""
    func = mcp.prompt()(func)  # apply MCP's decorator
    PROMPT_REGISTRY.append(func)
    return func
