#!/usr/bin/env python3
"""
Configure GPT Capabilities

This script configures the capabilities for the JFK Files Archivist GPT,
allowing customization of web browsing, file handling, and other features.
"""

import json
import os
import argparse
from typing import Dict, List, Optional

def load_config(config_path: str) -> Dict:
    """Load the GPT configuration from a JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config: Dict, config_path: str) -> None:
    """Save the updated GPT configuration to a JSON file."""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"Updated configuration saved to: {config_path}")

def update_capabilities(
    config: Dict,
    web_browsing: Optional[bool] = None,
    image_input: Optional[bool] = None,
    code_interpreter: Optional[bool] = None,
    file_upload: Optional[bool] = None,
    plugins: Optional[List[str]] = None
) -> Dict:
    """Update the capabilities configuration."""
    # Create capabilities dict if it doesn't exist
    if "capabilities" not in config:
        config["capabilities"] = {}
    
    # Update individual capabilities if specified
    if web_browsing is not None:
        config["capabilities"]["web_browsing"] = web_browsing
    
    if image_input is not None:
        config["capabilities"]["image_input"] = image_input
    
    if code_interpreter is not None:
        config["capabilities"]["code_interpreter"] = code_interpreter
    
    if file_upload is not None:
        config["capabilities"]["file_upload"] = file_upload
    
    if plugins is not None:
        config["capabilities"]["plugins"] = plugins
    
    return config

def main():
    parser = argparse.ArgumentParser(description="Configure GPT capabilities")
    parser.add_argument(
        "--config-path",
        default="lite_llm/gpt_configuration.json",
        help="Path to the GPT configuration JSON file"
    )
    parser.add_argument(
        "--web-browsing",
        type=lambda x: x.lower() == "true",
        help="Enable/disable web browsing capability"
    )
    parser.add_argument(
        "--image-input",
        type=lambda x: x.lower() == "true",
        help="Enable/disable image input capability"
    )
    parser.add_argument(
        "--code-interpreter",
        type=lambda x: x.lower() == "true",
        help="Enable/disable code interpreter capability"
    )
    parser.add_argument(
        "--file-upload",
        type=lambda x: x.lower() == "true",
        help="Enable/disable file upload capability"
    )
    parser.add_argument(
        "--add-plugin",
        action="append",
        help="Add a plugin to the GPT (can be used multiple times)"
    )
    parser.add_argument(
        "--clear-plugins",
        action="store_true",
        help="Clear all plugins from the GPT"
    )
    
    args = parser.parse_args()
    
    try:
        # Load existing configuration
        config = load_config(args.config_path)
        
        # Handle plugins
        plugins = None
        if args.clear_plugins:
            plugins = []
        elif args.add_plugin:
            plugins = config.get("capabilities", {}).get("plugins", [])
            plugins.extend(args.add_plugin)
            # Remove duplicates while preserving order
            plugins = list(dict.fromkeys(plugins))
        
        # Update capabilities
        updated_config = update_capabilities(
            config,
            web_browsing=args.web_browsing,
            image_input=args.image_input,
            code_interpreter=args.code_interpreter,
            file_upload=args.file_upload,
            plugins=plugins
        )
        
        # Save updated configuration
        save_config(updated_config, args.config_path)
        
        # Display current capabilities
        print("\nCurrent GPT Capabilities:")
        for capability, enabled in updated_config.get("capabilities", {}).items():
            if capability == "plugins":
                print(f"plugins: {', '.join(enabled) if enabled else 'None'}")
            else:
                print(f"{capability}: {'Enabled' if enabled else 'Disabled'}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
