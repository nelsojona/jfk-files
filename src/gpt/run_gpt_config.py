#!/usr/bin/env python3
"""
Run the GPT configuration generator

This script runs the GPTConfig class to generate and save the GPT configuration
to a JSON file in the lite_llm directory.
"""

from gpt_config import GPTConfig

def main():
    print("Generating JFK Files Archivist GPT configuration...")
    config = GPTConfig()
    output_file = config.save_config()
    print(f"Configuration saved to: {output_file}")
    print(config.get_config_summary())

if __name__ == "__main__":
    main()
