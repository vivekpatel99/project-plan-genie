import rootutils
from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger

try:
    from . import mcp_config

except ImportError:
    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.my_mcps import mcp_config


class MCPToolService:
    _instance = None
    _tools_cache = None
    _tools_by_name_cache = None

    def __new__(cls):
        """
        Enforce singleton pattern for this class.

        When called, this will either return an existing instance of the class
        or create a new one if it doesn't exist yet.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        logger.info("MCPToolService instance created.")
        return cls._instance

    async def get_tools(self):
        """Get tools, using cache if available."""
        if self._tools_cache is None:
            logger.info("Fetching tools from MCP...")
            await self._fetch_tools()
        logger.info("Tools fetched from MCP.")
        return self._tools_cache, self._tools_by_name_cache

    async def _fetch_tools(self) -> None:
        """Fetch tools from MCP and cache them."""
        client = MultiServerMCPClient(connections=mcp_config["mcpServers"])
        tools = await client.get_tools()
        self._tools_cache = tools
        self._tools_by_name_cache = {tool.name: tool for tool in tools if hasattr(tool, "name")}

    # def get_tools_metadata(self, tools) -> dict:
    #     """Extract serializable metadata from tools."""
    #     return {
    #         tool.name: {
    #             "name": tool.name,
    #             "description": getattr(tool, "description", ""),
    #         }
    #         for tool in tools
    #         if hasattr(tool, "name")
    #     }


# service = MCPToolService()
# tools, tools_by_name = await service.get_tools()
# print(tools)
# print(tools_by_name)
