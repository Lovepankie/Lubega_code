"""
Backup provider factory

Creates backup provider instances based on configuration.
"""

from typing import Dict
from .base import BackupProvider


def create_backup_provider(provider_config: Dict) -> BackupProvider:
    """
    Factory function to create backup providers

    Args:
        provider_config: Dictionary with provider configuration
                        Must contain 'type', 'name', and 'config' keys

    Returns:
        BackupProvider instance

    Raises:
        ValueError: If provider type is unknown

    Example:
        >>> config = {
        ...     'type': 'nextcloud',
        ...     'name': 'primary_backup',
        ...     'config': {'url': '...', 'username': '...'}
        ... }
        >>> provider = create_backup_provider(config)
    """
    provider_type = provider_config.get('type')
    provider_name = provider_config.get('name', 'unnamed')
    provider_settings = provider_config.get('config', {})

    if provider_type == 'nextcloud':
        from .providers.nextcloud import NextcloudProvider
        return NextcloudProvider(provider_name, provider_settings)

    elif provider_type == 'google_drive':
        from .providers.google_drive import GoogleDriveProvider
        return GoogleDriveProvider(provider_name, provider_settings)

    elif provider_type == 'local_archive':
        from .providers.local_archive import LocalArchiveProvider
        return LocalArchiveProvider(provider_name, provider_settings)

    else:
        raise ValueError(f"Unknown backup provider type: {provider_type}")
