# NFE Meter Data Backup Setup

Automated backup system for meter CSV data with multi-provider support.

---

## Overview

The NFE backup system automatically uploads meter data to cloud storage providers (Nextcloud, Google Drive, etc.) on a configurable schedule. It supports:

- **Multiple providers**: Run backups to Nextcloud, Google Drive, and local archives simultaneously
- **Smart syncing**: Only uploads changed/new files (efficient bandwidth usage)
- **Automated scheduling**: Runs every 6 hours via systemd timer
- **Configuration-driven**: Enable/disable providers via YAML config
- **Extensible**: Easy to add new backup providers

---

## Quick Start (Nextcloud)

### 1. Install rclone

```bash
sudo apt update
sudo apt install rclone -y
```

### 2. Configure Nextcloud Remote

```bash
rclone config
```

**Configuration wizard:**

1. **n** (New remote)
2. **name**: `nextcloud`
3. **Storage**: `webdav`
4. **URL**: `https://your-nextcloud-server.com/remote.php/dav/files/YOUR_USERNAME/`
5. **Vendor**: `1` (Nextcloud)
6. **User**: Your Nextcloud username
7. **Password**: Create app password in Nextcloud (Settings → Security → Devices & sessions → Create new app password)
8. Leave other options as default
9. **y** (Yes this is OK)
10. **q** (Quit config)

### 3. Test Connection

```bash
rclone lsd nextcloud:
```

You should see your Nextcloud folders listed.

### 4. Enable Backup in Configuration

Edit production config:

```bash
nano ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml
```

Ensure backup section is configured:

```yaml
backup:
  enabled: true
  schedule:
    frequency_hours: 6  # Run every 6 hours

  providers:
    - name: "nextcloud"
      type: "nextcloud"
      enabled: true
      config:
        rclone_remote: "nextcloud"
        remote_path: "/meter_backups"
```

### 5. Test Manual Backup

```bash
cd ~/nfe-modbus-energy-logger-prod
python3 -m src.backup.main config/config.prod.yaml
```

You should see:
```
============================================================
NFE Backup Cycle - 2026-03-29 15:30:00
============================================================

✅ Initialized provider: nextcloud (nextcloud)
📂 Found 12 files to backup

📤 Uploading to nextcloud...
✅ nextcloud: Uploaded 12 files (2.3 MB) in 4.5s

============================================================
Backup Complete: 1/1 providers successful
============================================================
```

### 6. Enable Automatic Backups

The backup service and timer are automatically installed during deployment. To start them:

```bash
# Start the timer (will run backup every 6 hours)
sudo systemctl start backup.timer

# Enable timer to start on boot
sudo systemctl enable backup.timer

# Verify timer is active
systemctl list-timers backup.timer
```

**Expected output:**
```
NEXT                         LEFT          LAST PASSED UNIT          ACTIVATES
Sat 2026-03-29 21:30:00 EAT  5h 59min left n/a  n/a    backup.timer  backup.service
```

---

## Management Commands

### Check Backup Status

```bash
# Check timer status
systemctl list-timers backup.timer

# View last backup logs
sudo journalctl -u backup.service -n 50

# Check next scheduled run
systemctl status backup.timer
```

### Manual Backup

```bash
# Trigger backup immediately
sudo systemctl start backup.service

# Watch backup execution
sudo journalctl -u backup.service -f
```

### Start/Stop Automatic Backups

```bash
# Start scheduled backups
sudo systemctl start backup.timer

# Stop scheduled backups
sudo systemctl stop backup.timer

# Enable on boot
sudo systemctl enable backup.timer

# Disable on boot
sudo systemctl disable backup.timer
```

---

## Configuration Details

### Backup Frequency

Change backup frequency in `config/config.prod.yaml`:

```yaml
backup:
  schedule:
    frequency_hours: 6  # Options: 1, 3, 6, 12, 24
```

**Note:** After changing frequency, reload the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl restart backup.timer
```

### Multiple Providers

Enable multiple backup destinations simultaneously:

```yaml
backup:
  enabled: true
  schedule:
    frequency_hours: 6

  providers:
    # Nextcloud (primary)
    - name: "nextcloud_primary"
      type: "nextcloud"
      enabled: true
      config:
        rclone_remote: "nextcloud"
        remote_path: "/meter_backups"

    # Google Drive (secondary) - Phase 2
    - name: "google_drive"
      type: "google_drive"
      enabled: false  # Not yet implemented
      config:
        credentials_file: "~/.config/backup/google-creds.json"
        folder_id: "1ABCxyz..."

    # Local archive (tertiary)
    - name: "local_nas"
      type: "local_archive"
      enabled: false  # Future feature
      config:
        archive_dir: "/mnt/nas/nfe-backups"
        retention_days: 90
```

Each provider uploads independently. If one fails, others continue.

---

## What Gets Backed Up

The backup system uploads all meter CSV files:

- **Current CSV files**: `meter_XXX/meter_XXX_YYYY-MM-DD.csv`
- **Compressed old files**: `meter_XXX/meter_XXX_YYYY-MM-DD.csv.gz`

**Not backed up:**
- State files (`data/state/*.json`) - these are transient
- Code files (`src/`) - managed via git
- Configuration files - site-specific, not in cloud

**Backup structure on Nextcloud:**
```
/meter_backups/
├── meter_001_2026-03-19.csv
├── meter_001_2026-03-18.csv.gz
├── meter_002_2026-03-19.csv
└── meter_002_2026-03-18.csv.gz
```

---

## Backup Behavior

### Smart Syncing

The system uses `rclone` with the `--update` flag:
- **Only uploads changed files** (checks modification time)
- **Replaces existing files** if local version is newer
- **Efficient bandwidth usage** (doesn't re-upload unchanged files)

Example:
```
First run:  Uploads all 12 files (2.3 MB)
Second run: Uploads 1 new file (195 KB) - only today's CSV changed
Third run:  Uploads 0 files - no changes detected
```

### Retry Logic

If backup fails:
- **No automatic retry** within the same cycle
- **Next attempt**: At next scheduled time (e.g., 6 hours later)
- **Errors logged**: Check with `journalctl -u backup.service`

For critical deployments, consider:
- Enabling multiple providers (if one fails, others succeed)
- Monitoring backup logs with external tools
- Setting up email alerts (Phase 3 feature)

---

## Accessing Backed-Up Data

### From Nextcloud Web Interface

1. Login to your Nextcloud instance
2. Navigate to `/meter_backups` folder
3. Download individual CSV files or entire folder as ZIP

### From Command Line (rclone)

```bash
# List backed-up files
rclone ls nextcloud:/meter_backups

# Download all backups to local directory
rclone copy nextcloud:/meter_backups ~/downloaded_backups

# Download specific meter's data
rclone copy nextcloud:/meter_backups/meter_001_*.csv ~/meter_001_data/
```

---

## Troubleshooting

### Backup Service Not Running

```bash
# Check service status
systemctl status backup.timer
sudo systemctl status backup.service

# Check for errors
sudo journalctl -u backup.service -n 100

# Restart timer
sudo systemctl restart backup.timer
```

### rclone Connection Errors

**Error: "Failed to create file system"**

```bash
# Test rclone config manually
rclone lsd nextcloud:

# Reconfigure if needed
rclone config reconnect nextcloud:
```

**Error: "Unauthorized" or "403 Forbidden"**

- App password may have expired
- Regenerate app password in Nextcloud (Settings → Security)
- Update rclone config: `rclone config`

**Error: "Timeout" or "Connection refused"**

- Check network connectivity
- Verify Nextcloud server URL is correct
- Test with browser: Visit your Nextcloud URL

### No Files Being Uploaded

**Check if meters are enabled:**

```bash
# View config
cat ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml | grep -A 5 "meters:"

# Check data directory
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_*/
```

**Check if backup is enabled in config:**

```bash
grep -A 10 "^backup:" ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml
```

### Verify Backup is Working

```bash
# Run manual backup and watch output
sudo systemctl start backup.service
sudo journalctl -u backup.service -f

# Check Nextcloud for new files
rclone ls nextcloud:/meter_backups
```

---

## Advanced Configuration

### Custom Remote Path

Change where files are stored on Nextcloud:

```yaml
providers:
  - name: "nextcloud"
    type: "nextcloud"
    enabled: true
    config:
      rclone_remote: "nextcloud"
      remote_path: "/Projects/NFE/Meter_Data"  # Custom path
```

### Multiple Nextcloud Servers

Configure multiple Nextcloud remotes:

```bash
# Configure second remote
rclone config
# name: nextcloud_backup
# ... (same as before, but different server)
```

```yaml
providers:
  - name: "nextcloud_primary"
    type: "nextcloud"
    enabled: true
    config:
      rclone_remote: "nextcloud"
      remote_path: "/meter_backups"

  - name: "nextcloud_secondary"
    type: "nextcloud"
    enabled: true
    config:
      rclone_remote: "nextcloud_backup"
      remote_path: "/nfe_data"
```

---

## Security Notes

### rclone Configuration Storage

rclone stores credentials in `~/.config/rclone/rclone.conf`. Permissions:

```bash
chmod 600 ~/.config/rclone/rclone.conf
```

### Nextcloud App Passwords

- Use **app passwords** instead of main password
- Create separate app password for each device/service
- Revoke compromised passwords easily in Nextcloud settings

### Network Security

- rclone uses **HTTPS** for all Nextcloud communication
- Credentials are **encrypted in transit**
- Consider using VPN for extra security

---

## Monitoring & Alerts (Phase 3)

**Coming soon:**
- Email notifications on backup failures
- Webhook alerts to Slack/Discord
- Backup health dashboard
- Automatic retry with exponential backoff

For now, monitor manually:

```bash
# Check backup logs daily
sudo journalctl -u backup.service --since "24 hours ago"

# Verify files in Nextcloud weekly
rclone ls nextcloud:/meter_backups | tail -20
```

---

## Next Steps

Once Nextcloud backup is working:

1. ✅ Let it run for 7 days to verify reliability
2. ✅ Check Nextcloud storage weekly to ensure files are uploading
3. ✅ Test restore procedure (download files from Nextcloud)
4. ⏳ **Phase 2**: Set up Google Drive as secondary backup
5. ⏳ **Phase 3**: Enable billing report generation (1st of month)

---

## Support

**Check logs:**
```bash
sudo journalctl -u backup.service -n 100
```

**Test manually:**
```bash
cd ~/nfe-modbus-energy-logger-prod
python3 -m src.backup.main config/config.prod.yaml
```

**Verify rclone:**
```bash
rclone lsd nextcloud:
rclone ls nextcloud:/meter_backups
```
