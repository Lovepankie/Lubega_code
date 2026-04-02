"""
Base classes for backup providers

Defines the abstract interface that all backup providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackupResult:
    """Result of a backup operation"""
    success: bool
    provider_name: str
    files_uploaded: int
    bytes_uploaded: int
    duration_seconds: float
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class BackupMetadata:
    """Metadata about a backed-up file"""
    filename: str
    size_bytes: int
    uploaded_at: datetime
    remote_path: str


class BackupProvider(ABC):
    """Abstract base class for backup providers"""

    def __init__(self, name: str, config: Dict):
        """
        Initialize backup provider

        Args:
            name: Provider instance name (e.g., "nextcloud_primary")
            config: Provider-specific configuration dictionary
        """
        self.name = name
        self.config = config

    @abstractmethod
    def upload_files(self, local_paths: List[str]) -> BackupResult:
        """
        Upload files to backup destination

        Args:
            local_paths: List of absolute paths to files to upload

        Returns:
            BackupResult with success status and details
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to backup destination

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def list_backups(self, path: Optional[str] = None) -> List[BackupMetadata]:
        """
        List backed-up files

        Args:
            path: Optional remote path to list (defaults to root)

        Returns:
            List of BackupMetadata objects
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}')>"
