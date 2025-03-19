#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checkpoint utilities for JFK Files Scraper.

This module provides functionality for saving and loading checkpoints
to support resumable operations.
"""

import os
import pickle
import logging
import time
from pathlib import Path

# Import custom exceptions
from src.utils.logging_utils import CheckpointError, track_error

# Initialize logger
logger = logging.getLogger("jfk_scraper.checkpoint")


def create_directories():
    """Create necessary directories for storing data."""
    os.makedirs("pdfs", exist_ok=True)
    os.makedirs("markdown", exist_ok=True)
    os.makedirs("json", exist_ok=True)
    os.makedirs("lite_llm", exist_ok=True)
    os.makedirs(".checkpoints", exist_ok=True)
    logger.info("Created output directories")


class CheckpointManager:
    """
    Manages checkpoints for resumable operations.
    
    This class provides methods for saving and loading checkpoints,
    with proper error handling and atomicity.
    """
    
    def __init__(self, checkpoint_dir=".checkpoints"):
        """
        Initialize the checkpoint manager.
        
        Args:
            checkpoint_dir (str): Directory to store checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    def save(self, data, checkpoint_name="checkpoint"):
        """
        Save checkpoint data to a file.
        
        Args:
            data: The data to save
            checkpoint_name (str): Name of the checkpoint file
            
        Returns:
            str: Path to the saved checkpoint file, or None if saving failed
        """
        try:
            checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.pickle"
            temp_path = self.checkpoint_dir / f"{checkpoint_name}.pickle.temp"
            
            # Write to temporary file first to ensure atomicity
            with open(temp_path, "wb") as f:
                pickle.dump(data, f)
            
            # Rename temporary file to final name
            os.rename(temp_path, checkpoint_path)
            
            logger.info(f"Checkpoint saved to {checkpoint_path}")
            return str(checkpoint_path)
            
        except Exception as e:
            error_message = f"Failed to save checkpoint {checkpoint_name}: {e}"
            logger.error(error_message)
            track_error("checkpoint", CheckpointError(error_message))
            return None
    
    def load(self, checkpoint_name="checkpoint"):
        """
        Load checkpoint data from a file.
        
        Args:
            checkpoint_name (str): Name of the checkpoint file
            
        Returns:
            The loaded checkpoint data, or None if loading failed
        """
        try:
            checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.pickle"
            
            if not checkpoint_path.exists():
                logger.info(f"Checkpoint {checkpoint_path} does not exist")
                return None
            
            with open(checkpoint_path, "rb") as f:
                data = pickle.load(f)
            
            logger.info(f"Checkpoint loaded from {checkpoint_path}")
            return data
            
        except Exception as e:
            error_message = f"Failed to load checkpoint {checkpoint_name}: {e}"
            logger.error(error_message)
            track_error("checkpoint", CheckpointError(error_message))
            return None
    
    def list_checkpoints(self):
        """
        List all available checkpoints.
        
        Returns:
            list: List of checkpoint names
        """
        try:
            checkpoints = []
            for file in self.checkpoint_dir.glob("*.pickle"):
                checkpoints.append(file.stem)
            return checkpoints
        except Exception as e:
            error_message = f"Failed to list checkpoints: {e}"
            logger.error(error_message)
            track_error("checkpoint", CheckpointError(error_message))
            return []
    
    def delete(self, checkpoint_name):
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_name (str): Name of the checkpoint to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.pickle"
            
            if not checkpoint_path.exists():
                logger.info(f"Checkpoint {checkpoint_path} does not exist")
                return False
            
            os.remove(checkpoint_path)
            logger.info(f"Checkpoint {checkpoint_path} deleted")
            return True
            
        except Exception as e:
            error_message = f"Failed to delete checkpoint {checkpoint_name}: {e}"
            logger.error(error_message)
            track_error("checkpoint", CheckpointError(error_message))
            return False


# Global checkpoint manager instance
_checkpoint_manager = None


def get_checkpoint_manager():
    """
    Get the global checkpoint manager instance.
    
    Returns:
        CheckpointManager: The global checkpoint manager instance
    """
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


def save_checkpoint(data, checkpoint_name="checkpoint"):
    """
    Save checkpoint data using the global checkpoint manager.
    
    Args:
        data: The data to save
        checkpoint_name (str): Name of the checkpoint file
        
    Returns:
        str: Path to the saved checkpoint file, or None if saving failed
    """
    return get_checkpoint_manager().save(data, checkpoint_name)


def load_checkpoint(checkpoint_name="checkpoint"):
    """
    Load checkpoint data using the global checkpoint manager.
    
    Args:
        checkpoint_name (str): Name of the checkpoint file
        
    Returns:
        The loaded checkpoint data, or None if loading failed
    """
    return get_checkpoint_manager().load(checkpoint_name)