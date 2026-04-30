#!/usr/bin/env python3
"""
Path Manager for YOLO Vision Pipeline
Centralizes all path configuration from configs/paths.yaml
"""

import os
import sys
from pathlib import Path
import yaml
from typing import Optional, Dict, Any


class PathManager:
    """Manages all project paths from configuration."""
    
    _instance = None
    _config = None
    _project_root = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load paths configuration from YAML file."""
        if cls._config is not None:
            return cls._config
        
        # Determine config file path
        if config_path is None:
            # Try to find configs/paths.yaml from current directory or parent directories
            current_dir = Path.cwd()
            found = False
            
            for parent in [current_dir] + list(current_dir.parents):
                potential_config = parent / "configs" / "paths.yaml"
                if potential_config.exists():
                    config_path = str(potential_config)
                    found = True
                    break
            
            if not found:
                raise FileNotFoundError(
                    "configs/paths.yaml not found. "
                    "Make sure you're running from the project root directory."
                )
        
        # Load YAML file
        with open(config_path, 'r', encoding='utf-8') as f:
            cls._config = yaml.safe_load(f)
        
        return cls._config
    
    @classmethod
    def get_project_root(cls) -> Path:
        """Get project root directory."""
        if cls._project_root is not None:
            return cls._project_root
        
        config = cls.load_config()
        project_root = config.get("project_root")
        
        if project_root and project_root != "null":
            cls._project_root = Path(project_root)
        else:
            # Auto-detect: look for configs/paths.yaml
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                if (parent / "configs" / "paths.yaml").exists():
                    cls._project_root = parent
                    break
            
            if cls._project_root is None:
                cls._project_root = current_dir
        
        return cls._project_root
    
    @classmethod
    def resolve_path(cls, path_str: str) -> Path:
        """Resolve a path string to absolute Path object."""
        if not path_str:
            return None
        
        path = Path(path_str)
        
        # If already absolute, return as-is
        if path.is_absolute():
            return path
        
        # Otherwise resolve relative to project root
        return cls.get_project_root() / path
    
    @classmethod
    def get(cls, key_path: str, default: Optional[str] = None) -> Optional[Path]:
        """
        Get a path from configuration by dot-notation key.
        
        Examples:
            paths.get("models.best_pt")
            paths.get("dataset.train_images")
            paths.get("configs.data")
        """
        config = cls.load_config()
        
        # Navigate through nested dictionary
        keys = key_path.split(".")
        value = config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        
        if value is None:
            return default
        
        return cls.resolve_path(str(value))
    
    @classmethod
    def get_str(cls, key_path: str, default: Optional[str] = None) -> Optional[str]:
        """Get a path as string instead of Path object."""
        path = cls.get(key_path, default)
        return str(path) if path else default
    
    @classmethod
    def ensure_dir(cls, key_path: str) -> Path:
        """Get path and ensure directory exists."""
        path = cls.get(key_path)
        if path:
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    @classmethod
    def get_all(cls, section: str) -> Dict[str, Path]:
        """Get all paths in a section."""
        config = cls.load_config()
        section_config = config.get(section, {})
        
        result = {}
        for key, value in section_config.items():
            if isinstance(value, str):
                result[key] = cls.resolve_path(value)
        
        return result
    
    @classmethod
    def print_config(cls):
        """Print current path configuration."""
        config = cls.load_config()
        project_root = cls.get_project_root()
        
        print("=" * 70)
        print("YOLO Vision Pipeline - Path Configuration")
        print("=" * 70)
        print(f"Project Root: {project_root}\n")
        
        def print_dict(d, indent=0):
            for key, value in d.items():
                if key == "project_root":
                    continue
                if isinstance(value, dict):
                    print("  " * indent + f"[{key}]")
                    print_dict(value, indent + 1)
                elif isinstance(value, (str, int, float, bool)):
                    if isinstance(value, str) and not value.startswith("/"):
                        resolved = cls.resolve_path(value)
                        print("  " * indent + f"  {key}: {value} → {resolved}")
                    else:
                        print("  " * indent + f"  {key}: {value}")
        
        print_dict(config)
        print("=" * 70)


# Convenience instance
paths = PathManager()


if __name__ == "__main__":
    # Print current configuration
    PathManager.print_config()
    
    # Examples
    print("\nExamples:")
    print(f"  Best PT model: {paths.get('models.best_pt')}")
    print(f"  Train images: {paths.get('dataset.train_images')}")
    print(f"  ONNX export: {paths.get('models.best_onnx')}")
    print(f"  RKNN output: {paths.get('models.best_rknn')}")
