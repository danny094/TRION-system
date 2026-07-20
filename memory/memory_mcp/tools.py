from .tool_groups.memory_tools import register_memory_tools
from .tool_groups.memory_admin_tools import register_memory_admin_tools
from .tool_groups.embedding_tools import register_embedding_tools
from .tool_groups.graph_tools import register_graph_tools
from .tool_groups.graph_admin_tools import register_graph_admin_tools
from .tool_groups.workspace_tools import register_workspace_tools
from .tool_groups.skill_tools import register_skill_tools
from .tool_groups.secret_tools import register_secret_tools
from .tool_groups.conversation_meta_tools import register_conversation_meta_tools
from .tool_groups.maintenance_tools import register_maintenance_tools


def register_tools(mcp) -> None:
    register_memory_tools(mcp)
    register_memory_admin_tools(mcp)
    register_embedding_tools(mcp)
    register_graph_tools(mcp)
    register_graph_admin_tools(mcp)
    register_workspace_tools(mcp)
    register_skill_tools(mcp)
    register_secret_tools(mcp)
    register_conversation_meta_tools(mcp)
    register_maintenance_tools(mcp)
