import json
import typing as t
from inspect import Signature
from typing import Sequence, TypeAlias

from agno.tools.toolkit import Toolkit
from typing_extensions import Protocol
from pydantic import validate_call

from composio.core.provider import AgenticProvider, AgenticProviderExecuteFn
from composio.types import Tool
from composio.utils import shared


class ToolFunction(Protocol):
    """Protocol for tool functions with required attributes."""

    __signature__: Signature
    __annotations__: t.Dict[str, t.Any]
    __doc__: str

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> str: ...


class SerializableToolFunction:
    """A serializable wrapper for tool functions that can be pickled."""
    
    def __init__(self, tool_slug: str, signature: Signature, annotations: dict, docstring: str, name: str):
        self.tool_slug = tool_slug
        self.__signature__ = signature
        self.__annotations__ = annotations
        self.__doc__ = docstring
        self.__name__ = name
        self._execute_tool = None
        
    @validate_call
    def __call__(self, *args, **kwargs) -> str:
        # Check if execute function is bound
        if self._execute_tool is None:
            raise NotImplementedError("This function needs to be bound to an execute function at runtime")
        
        # Bind the arguments to the signature
        bound_args = self.__signature__.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        result = self._execute_tool(self.tool_slug, bound_args.arguments)
        if not result.get("successful", False):
            raise Exception(result.get("error", "Tool execution failed"))
        
        return json.dumps(result.get("data", {}))
    
    def bind_execute_function(self, execute_tool: AgenticProviderExecuteFn):
        """Bind the actual execution function at runtime."""
        self._execute_tool = execute_tool
        return self


# Define the tool collection type for Agno
AgnoToolCollection: TypeAlias = t.List[Toolkit]

class AgnoProvider(AgenticProvider[Toolkit, AgnoToolCollection], name="agno"):
    """Agno provider for Composio"""
    
    def __init__(self, api_key: t.Optional[str] = None, base_url: t.Optional[str] = None):
        """Initialize AgnoProvider with Composio client."""
        kwargs = {}
        if api_key is not None:
            kwargs["api_key"] = api_key
        if base_url is not None:
            kwargs["base_url"] = base_url
        super().__init__(**kwargs)
    
    def _create_tool_function(self, tool: Tool, execute_tool: AgenticProviderExecuteFn) -> SerializableToolFunction:
        """Create a tool function from a Tool object"""
        description = tool.description or ""
        parameters = tool.input_parameters
        
        # Get function parameters from schema
        params = shared.get_signature_format_from_schema_params(
            schema_params=parameters,
            skip_default=False,
        )
        
        # Create function signature and annotations
        sig = Signature(parameters=params)
        annotations = {p.name: p.annotation for p in params}
        annotations["return"] = str  # Add return type annotation
        
        # Format docstring in Agno standard format
        docstring_parts = [description, "\nArgs:"]
        if parameters and "properties" in parameters and isinstance(parameters["properties"], dict):
            for param_name, param_info in parameters["properties"].items():
                param_desc = param_info.get("description", "No description available")
                param_type = param_info.get("type", "any")
                docstring_parts.append(f"    {param_name} ({param_type}): {param_desc}")
        
        docstring_parts.append(
            "\nReturns:\n    str: JSON string containing the function execution result"
        )
        docstring = "\n".join(docstring_parts)
        
        # Create the serializable function
        func = SerializableToolFunction(
            tool_slug=tool.slug,
            signature=sig,
            annotations=annotations,
            docstring=docstring,
            name=tool.slug.lower()
        )
        
        # Bind the execute function
        func.bind_execute_function(execute_tool)
        
        return func
    
    def _extract_app_name(self, tool_slug: str) -> str:
        """Extract app name from tool slug with better logic"""
        # Define app name mappings for special cases
        app_mappings = {
            'GOOGLEDRIVE': 'GOOGLE_DRIVE',
            'GOOGLECALENDAR': 'GOOGLE_CALENDAR', 
            'GOOGLE_MAPS': 'GOOGLE_MAPS',
            'ONE_DRIVE': 'ONE_DRIVE',
            'COMPOSIO_SEARCH': 'COMPOSIO_SEARCH'
        }
        
        # Check for multi-word app prefixes first
        for prefix in ['GOOGLE_MAPS', 'ONE_DRIVE', 'COMPOSIO_SEARCH', 'GOOGLECALENDAR', 'GOOGLEDRIVE']:
            if tool_slug.startswith(prefix):
                return app_mappings.get(prefix, prefix)
        
        # Fallback to first word
        first_part = tool_slug.split('_')[0] if '_' in tool_slug else tool_slug
        return app_mappings.get(first_part, first_part)

    def wrap_tool(self, tool: Tool, execute_tool: AgenticProviderExecuteFn) -> Toolkit:
        """Transform a single tool with execute function (kept for compatibility)"""
        app_name = self._extract_app_name(tool.slug)
        toolkit = Toolkit(name=app_name)
        func = self._create_tool_function(tool, execute_tool)
        toolkit.register(func)
        return toolkit
    
    def wrap_tools(
        self,
        tools: Sequence[Tool],
        execute_tool: AgenticProviderExecuteFn
    ) -> AgnoToolCollection:
        """Transform a collection of tools with execute function"""
        # Group tools by their app/integration
        app_tools = {}
        
        for tool in tools:
            app_name = self._extract_app_name(tool.slug)
            
            if app_name not in app_tools:
                app_tools[app_name] = []
            app_tools[app_name].append(tool)
        
        # Create one toolkit per app with all its tools
        toolkits = []
        for app_name, app_tool_list in app_tools.items():
            toolkit = Toolkit(name=app_name)
            
            for tool in app_tool_list:
                func = self._create_tool_function(tool, execute_tool)
                toolkit.register(func)
            
            toolkits.append(toolkit)
        
        return toolkits
