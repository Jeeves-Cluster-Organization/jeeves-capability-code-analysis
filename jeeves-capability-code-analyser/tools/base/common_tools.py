"""Common utility tools for debugging and system operations."""

from typing import Dict, Any, Optional

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol
# Constitutional imports - from mission_system contracts layer
from jeeves_mission_system.contracts import PersistenceProtocol
from tools.registry import tool_registry, RiskLevel


class CommonTools:
    """Common utility tools."""

    def __init__(self, db: PersistenceProtocol, logger: Optional[LoggerProtocol] = None):
        self.db = db
        self._logger = logger or get_logger()

    async def echo(
        self,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Echo back the input (for testing and debugging).

        Args:
            **kwargs: Any parameters

        Returns:
            StandardToolResult (as dict) with the echoed payload
        """
        from jeeves_mission_system.contracts import StandardToolResult

        self._logger.info("echo", payload=kwargs)

        return StandardToolResult.success(
            data={"payload": kwargs},
            message=f"ECHO: {kwargs!r}"
        ).model_dump()

    async def health_check(
        self
    ) -> Dict[str, Any]:
        """
        Perform a health check (database connectivity, etc.).

        Returns:
            StandardToolResult (as dict) with health status
        """
        from jeeves_mission_system.contracts import StandardToolResult

        try:
            # Check database connectivity
            result = await self.db.fetch_one("SELECT 1 as test")

            if result and result.get("test") == 1:
                db_status = "healthy"
            else:
                db_status = "unhealthy"

        except Exception as e:
            db_status = "error"
            self._logger.error("health_check_db_failed", error=str(e))

        self._logger.info("health_check", db_status=db_status)

        return StandardToolResult.success(
            data={"database": db_status},
            message=f"System health: database={db_status}"
        ).model_dump()

    async def get_system_info(
        self
    ) -> Dict[str, Any]:
        """
        Get system information (tables, counts, etc.).

        Returns:
            StandardToolResult (as dict) with system stats
        """
        from jeeves_mission_system.contracts import StandardToolResult, ToolErrorDetails

        try:
            # Get table counts
            tasks_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM tasks")
            kv_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM kv_store")
            journal_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM journal_entries")
            requests_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM requests")

            self._logger.info("system_info_retrieved")

            return StandardToolResult.success(
                data={
                    "tables": {
                        "tasks": tasks_count.get("count", 0) if tasks_count else 0,
                        "kv_store": kv_count.get("count", 0) if kv_count else 0,
                        "journal_entries": journal_count.get("count", 0) if journal_count else 0,
                        "requests": requests_count.get("count", 0) if requests_count else 0
                    }
                },
                message="System information retrieved"
            ).model_dump()

        except Exception as e:
            self._logger.error("system_info_failed", error=str(e))
            return StandardToolResult.failure(
                error=ToolErrorDetails.from_exception(e, recoverable=True),
                message=f"Failed to get system info: {str(e)}"
            ).model_dump()


# Register tools with the registry
def register_common_tools(db: PersistenceProtocol, registry=None):
    """Register all common tools with the specified or global tool registry."""
    target_registry = registry if registry is not None else tool_registry
    tools = CommonTools(db)

    @target_registry.register(
        name="echo",
        description="Echo back the input (for testing and debugging)",
        parameters={
            "**kwargs": "Any parameters (all will be echoed back)"
        },
        risk_level=RiskLevel.READ_ONLY
    )
    async def echo(**kwargs):
        return await tools.echo(**kwargs)

    @target_registry.register(
        name="health_check",
        description="Perform a health check on the system",
        parameters={},
        risk_level=RiskLevel.READ_ONLY
    )
    async def health_check(**kwargs):
        return await tools.health_check()

    @target_registry.register(
        name="system_info",
        description="Get system information (table counts, stats)",
        parameters={},
        risk_level=RiskLevel.READ_ONLY
    )
    async def system_info(**kwargs):
        return await tools.get_system_info()

    return tools
