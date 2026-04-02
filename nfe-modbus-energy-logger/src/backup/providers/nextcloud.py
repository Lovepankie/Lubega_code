"""
Nextcloud backup provider using rclone

Uploads meter data to Nextcloud server via WebDAV using rclone.
"""

import subprocess
import os
import time
from typing import List, Dict, Optional
from datetime import datetime

from ..base import BackupProvider, BackupResult, BackupMetadata


class NextcloudProvider(BackupProvider):
    """Nextcloud backup provider using rclone"""

    def __init__(self, name: str, config: Dict):
        """
        Initialize Nextcloud provider

        Config keys:
            - rclone_remote: Name of rclone remote (e.g., "nextcloud")
            - remote_path: Path on Nextcloud (e.g., "/meter_backups")
            - url: Nextcloud URL (optional, for test_connection)
            - username: Nextcloud username (optional, for test_connection)
        """
        super().__init__(name, config)
        self.rclone_remote = config.get('rclone_remote', 'nextcloud')
        self.remote_path = config.get('remote_path', '/meter_backups')

        # Ensure remote path doesn't have trailing slash
        self.remote_path = self.remote_path.rstrip('/')

    def upload_files(self, local_paths: List[str]) -> BackupResult:
        """
        Upload files to Nextcloud using rclone sync

        Uses rclone sync with --update flag to only upload changed files.
        """
        start_time = time.time()
        files_uploaded = 0
        bytes_uploaded = 0
        error_message = None

        try:
            # Calculate total size before upload
            for path in local_paths:
                if os.path.isfile(path):
                    bytes_uploaded += os.path.getsize(path)
                    files_uploaded += 1
                elif os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            filepath = os.path.join(root, file)
                            bytes_uploaded += os.path.getsize(filepath)
                            files_uploaded += 1

            # Build rclone command
            # Use sync to mirror source to destination
            for local_path in local_paths:
                # Determine if path is file or directory
                if os.path.isfile(local_path):
                    # For single file, sync its parent directory
                    local_dir = os.path.dirname(local_path)
                    filename = os.path.basename(local_path)
                    remote_dest = f"{self.rclone_remote}:{self.remote_path}"

                    cmd = [
                        'rclone', 'copy',
                        local_path,
                        remote_dest,
                        '--update',  # Only copy if source is newer
                        '--transfers', '4',
                        '--checkers', '8',
                        '--stats', '0',  # Disable stats output
                        '--log-level', 'ERROR'  # Only show errors
                    ]
                elif os.path.isdir(local_path):
                    # For directory, sync entire directory
                    remote_dest = f"{self.rclone_remote}:{self.remote_path}"

                    cmd = [
                        'rclone', 'sync',
                        local_path,
                        remote_dest,
                        '--update',
                        '--transfers', '4',
                        '--checkers', '8',
                        '--stats', '0',
                        '--log-level', 'ERROR'
                    ]
                else:
                    print(f"⚠️  Skipping non-existent path: {local_path}")
                    continue

                # Execute rclone
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                if result.returncode != 0:
                    error_message = f"rclone error: {result.stderr}"
                    print(f"❌ rclone failed: {error_message}")
                    break

            duration = time.time() - start_time

            if error_message:
                return BackupResult(
                    success=False,
                    provider_name=self.name,
                    files_uploaded=0,
                    bytes_uploaded=0,
                    duration_seconds=duration,
                    error_message=error_message
                )

            return BackupResult(
                success=True,
                provider_name=self.name,
                files_uploaded=files_uploaded,
                bytes_uploaded=bytes_uploaded,
                duration_seconds=duration
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return BackupResult(
                success=False,
                provider_name=self.name,
                files_uploaded=0,
                bytes_uploaded=0,
                duration_seconds=duration,
                error_message="Upload timed out after 5 minutes"
            )

        except Exception as e:
            duration = time.time() - start_time
            return BackupResult(
                success=False,
                provider_name=self.name,
                files_uploaded=0,
                bytes_uploaded=0,
                duration_seconds=duration,
                error_message=str(e)
            )

    def test_connection(self) -> bool:
        """
        Test connection to Nextcloud by listing remote directory
        """
        try:
            cmd = [
                'rclone', 'lsd',
                f"{self.rclone_remote}:{self.remote_path}",
                '--max-depth', '1'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.returncode == 0

        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

    def list_backups(self, path: Optional[str] = None) -> List[BackupMetadata]:
        """
        List backed-up files in Nextcloud
        """
        try:
            remote_path = path if path else self.remote_path

            cmd = [
                'rclone', 'lsjson',
                f"{self.rclone_remote}:{remote_path}",
                '--recursive'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            import json
            files_data = json.loads(result.stdout)

            backups = []
            for file_info in files_data:
                if file_info['IsDir']:
                    continue

                backups.append(BackupMetadata(
                    filename=file_info['Name'],
                    size_bytes=file_info['Size'],
                    uploaded_at=datetime.fromisoformat(file_info['ModTime'].replace('Z', '+00:00')),
                    remote_path=file_info['Path']
                ))

            return backups

        except Exception as e:
            print(f"❌ List backups failed: {e}")
            return []
