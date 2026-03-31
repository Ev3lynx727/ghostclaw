"""
Agent SDK Serializers

Custom JSON serialization/deserialization for Pydantic models.
Handles special types: UUID, Path, datetime

"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Type, TypeVar
from uuid import UUID

from pydantic import TypeAdapter


T = TypeVar("T")


class AgentSDKEncoder(json.JSONEncoder):
    """Custom JSON encoder for agent-sdk types."""
    
    def default(self, obj: Any) -> Any:
        """Handle custom types."""
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, datetime):
            # ISO format with Z suffix for UTC
            return obj.isoformat() + "Z" if obj.tzinfo is None else obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def serialize_to_json(data: Any, **kwargs) -> str:
    """
    Serialize agent-sdk model to JSON string.
    
    Args:
        data: Pydantic model or dict to serialize
        **kwargs: Additional json.dumps arguments
    
    Returns:
        JSON string
    """
    return json.dumps(
        data,
        cls=AgentSDKEncoder,
        indent=2,
        **kwargs
    )


def deserialize_from_json(json_str: str, model_class: Type[T]) -> T:
    """
    Deserialize JSON string to Pydantic model.
    
    Args:
        json_str: JSON string
        model_class: Target Pydantic model class
    
    Returns:
        Deserialized model instance
    
    Example:
        >>> json_data = '{"id": "abc-123", "name": "test-agent"}'
        >>> agent = deserialize_from_json(json_data, AgentMetadata)
    """
    data = json.loads(json_str)
    adapter = TypeAdapter(model_class)
    return adapter.validate_python(data)


def model_to_json_dict(model: Any) -> dict:
    """
    Convert Pydantic model to JSON-safe dict.
    
    Uses model_dump() with custom serializers.
    """
    if hasattr(model, "model_dump"):
        # Pydantic v2
        return model.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=False,
        )
    elif hasattr(model, "dict"):
        # Pydantic v1 fallback
        return model.dict(by_alias=True)
    else:
        return dict(model)


def json_dict_to_model(data: dict, model_class: Type[T]) -> T:
    """
    Convert JSON dict to Pydantic model.
    
    Handles type coercion for special fields.
    """
    adapter = TypeAdapter(model_class)
    return adapter.validate_python(data)


class ModelSerializer:
    """
    Helper class for consistent model serialization across agent-sdk.
    
    Example:
        >>> serializer = ModelSerializer(AgentIdentity)
        >>> json_str = serializer.serialize(agent_identity)
        >>> agent = serializer.deserialize(json_str)
    """
    
    def __init__(self, model_class: Type[T]):
        """Initialize serializer for specific model class."""
        self.model_class = model_class
        self.adapter = TypeAdapter(model_class)
    
    def serialize(self, model: T, pretty: bool = True) -> str:
        """Serialize model to JSON string."""
        data = model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()
        return json.dumps(
            data,
            cls=AgentSDKEncoder,
            indent=2 if pretty else None
        )
    
    def deserialize(self, json_str: str) -> T:
        """Deserialize JSON string to model."""
        data = json.loads(json_str)
        return self.adapter.validate_python(data)
    
    def serialize_file(self, model: T, file_path: Path) -> None:
        """Serialize model to JSON file."""
        json_str = self.serialize(model, pretty=True)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json_str, encoding="utf-8")
    
    def deserialize_file(self, file_path: Path) -> T:
        """Deserialize model from JSON file."""
        json_str = file_path.read_text(encoding="utf-8")
        return self.deserialize(json_str)


__all__ = [
    "AgentSDKEncoder",
    "serialize_to_json",
    "deserialize_from_json",
    "model_to_json_dict",
    "json_dict_to_model",
    "ModelSerializer",
]
