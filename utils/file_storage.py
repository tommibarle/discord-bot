import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

STORAGE_DIR = "document_storage"

def ensure_storage_dir():
    """Ensure the storage directory exists"""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
        logger.debug(f"Created storage directory: {STORAGE_DIR}")

def get_user_storage_path(user_id: str) -> str:
    """Get the storage path for a specific user"""
    return os.path.join(STORAGE_DIR, f"user_{user_id}")

def save_document(user_id: str, name: str, content: bytes, context: str, temp_dir: Optional[str] = None) -> bool:
    """
    Save a document to file storage.

    Args:
        user_id (str): The ID of the user
        name (str): The name/identifier for the document
        content (bytes): The document content
        context (str): The context/type of the document
        temp_dir (Optional[str]): Optional temporary directory path

    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        ensure_storage_dir()
        save_dir = temp_dir if temp_dir else get_user_storage_path(user_id)

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            logger.debug(f"Created directory: {save_dir}")

        # Create a unique filename using timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{name}_{timestamp}"

        # Save content file
        content_path = os.path.join(save_dir, f"{base_filename}.txt")
        logger.debug(f"Saving content to: {content_path}")
        with open(content_path, 'wb') as f:
            f.write(content)

        # Save metadata
        metadata = {
            'name': name,
            'context': context,
            'timestamp': timestamp,
            'content_file': f"{base_filename}.txt"
        }
        meta_path = os.path.join(save_dir, f"{base_filename}.json")
        logger.debug(f"Saving metadata to: {meta_path}")
        with open(meta_path, 'w') as f:
            json.dump(metadata, f)

        logger.debug(f"Successfully saved document {base_filename}")
        return True

    except Exception as e:
        logger.error(f"Error saving document: {e}", exc_info=True)
        return False

def save_documents(documents: List[Dict], name: str, user_id: str) -> bool:
    """
    Save multiple documents to file storage.

    Args:
        documents (List[Dict]): List of documents with 'content' and 'context'
        name (str): The name/identifier for the document group
        user_id (str): The ID of the user

    Returns:
        bool: True if all saves were successful, False otherwise
    """
    try:
        logger.debug(f"Attempting to save {len(documents)} documents for {name}")
        for idx, doc in enumerate(documents, 1):
            logger.debug(f"Saving document {idx}/{len(documents)}")
            success = save_document(
                user_id=user_id,
                name=name,
                content=doc['content'],
                context=doc['context']
            )
            if not success:
                logger.error(f"Failed to save document {idx}")
                return False
        logger.debug("Successfully saved all documents")
        return True
    except Exception as e:
        logger.error(f"Error in batch document save: {e}", exc_info=True)
        return False