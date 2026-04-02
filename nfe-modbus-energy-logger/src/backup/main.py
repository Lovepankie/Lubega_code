"""
Backup orchestrator - Main entry point for backup service

Coordinates backup operations across multiple providers.
"""

import os
import sys
import glob
import yaml
from datetime import datetime
from typing import List

from .factory import create_backup_provider
from .base import BackupProvider


class BackupOrchestrator:
    """Orchestrates backup operations for meter data"""

    def __init__(self, config_path: str):
        """
        Initialize backup orchestrator

        Args:
            config_path: Path to config.yaml file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)

        self.meters_cfg = self.cfg.get('meters', [])
        self.backup_cfg = self.cfg.get('backup', {})
        self.logging_cfg = self.cfg.get('logging', {})

        # Check if backup is enabled
        if not self.backup_cfg.get('enabled', False):
            print("⚠️  Backup is disabled in configuration")
            sys.exit(0)

        # Initialize enabled providers
        self.providers: List[BackupProvider] = []
        for provider_cfg in self.backup_cfg.get('providers', []):
            if provider_cfg.get('enabled', True):
                try:
                    provider = create_backup_provider(provider_cfg)
                    self.providers.append(provider)
                    print(f"✅ Initialized provider: {provider.name} ({provider_cfg['type']})")
                except Exception as e:
                    print(f"❌ Failed to initialize provider {provider_cfg.get('name', 'unknown')}: {e}")

        if not self.providers:
            print("❌ No backup providers enabled")
            sys.exit(1)

    def run_backup_cycle(self):
        """
        Execute backup cycle

        Called by systemd timer periodically to backup meter data.
        """
        print(f"\n{'='*60}")
        print(f"NFE Backup Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        try:
            # 1. Collect meter CSV files
            files_to_backup = self._collect_meter_files()

            if not files_to_backup:
                print("⚠️  No files to backup")
                return

            print(f"📂 Found {len(files_to_backup)} files to backup")

            # 2. Upload to all enabled providers
            success_count = 0
            for provider in self.providers:
                print(f"\n📤 Uploading to {provider.name}...")

                result = provider.upload_files(files_to_backup)

                if result.success:
                    print(f"✅ {provider.name}: Uploaded {result.files_uploaded} files "
                          f"({self._format_bytes(result.bytes_uploaded)}) "
                          f"in {result.duration_seconds:.1f}s")
                    success_count += 1
                else:
                    print(f"❌ {provider.name}: Failed - {result.error_message}")

            # 3. Summary
            print(f"\n{'='*60}")
            print(f"Backup Complete: {success_count}/{len(self.providers)} providers successful")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"❌ Backup cycle failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def _collect_meter_files(self) -> List[str]:
        """
        Collect all meter CSV files for backup

        Returns:
            List of absolute file paths
        """
        files = []
        base_dir = self.logging_cfg.get('base_dir', 'data')

        # Collect files for each enabled meter
        for meter_cfg in self.meters_cfg:
            if not meter_cfg.get('enabled', True):
                continue

            meter_id = meter_cfg['id']
            meter_dir = os.path.join(base_dir, f"meter_{meter_id:03d}")

            if not os.path.isdir(meter_dir):
                print(f"⚠️  Meter directory not found: {meter_dir}")
                continue

            # Find all CSV files (current and compressed)
            csv_files = glob.glob(os.path.join(meter_dir, "*.csv"))
            gz_files = glob.glob(os.path.join(meter_dir, "*.csv.gz"))

            files.extend(csv_files)
            files.extend(gz_files)

        # Convert to absolute paths
        files = [os.path.abspath(f) for f in files]

        return files

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes as human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"

    def test_providers(self):
        """
        Test connection to all providers

        Used for manual testing and diagnostics.
        """
        print("Testing backup providers...\n")

        all_ok = True
        for provider in self.providers:
            print(f"Testing {provider.name}...", end=" ")

            if provider.test_connection():
                print("✅ Connected")
            else:
                print("❌ Failed")
                all_ok = False

        print()
        return all_ok


def main():
    """Main entry point for backup service"""
    if len(sys.argv) < 2:
        print("Usage: python3 -m src.backup.main <config.yaml>")
        sys.exit(1)

    config_path = sys.argv[1]

    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    # Initialize orchestrator
    orchestrator = BackupOrchestrator(config_path)

    # Run backup cycle
    orchestrator.run_backup_cycle()


if __name__ == '__main__':
    main()
