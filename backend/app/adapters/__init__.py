"""Concrete implementations of versioned internal adapter contracts."""

from app.adapters.chatgpt import ChatGPTAdapter
from app.adapters.filesystem_tools import (
    FilesystemListToolAdapter,
    FilesystemReadTextToolAdapter,
    FilesystemStatToolAdapter,
)
from app.adapters.local_ai import LocalAIAdapter
from app.adapters.project_snapshot_module import ProjectSnapshotModuleAdapter
from app.adapters.standard_tool import StandardToolAdapter
from app.adapters.system_health_tool import SystemHealthToolAdapter
from app.adapters.system_info_tool import SystemInfoToolAdapter
from app.adapters.workspace_overview_module import WorkspaceOverviewModuleAdapter

__all__ = [
    "ChatGPTAdapter",
    "FilesystemListToolAdapter",
    "FilesystemReadTextToolAdapter",
    "FilesystemStatToolAdapter",
    "LocalAIAdapter",
    "ProjectSnapshotModuleAdapter",
    "StandardToolAdapter",
    "SystemHealthToolAdapter",
    "SystemInfoToolAdapter",
    "WorkspaceOverviewModuleAdapter",
]
