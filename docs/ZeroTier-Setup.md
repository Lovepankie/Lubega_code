# ZeroTier Remote Access Guide

This guide explains how to connect to the NFE Raspberry Pi from anywhere in the world using ZeroTier. It covers both SSH access and troubleshooting common issues.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Network Information](#network-information)
3. [Installing ZeroTier on Your Computer](#installing-zerotier-on-your-computer)
4. [Joining the Network](#joining-the-network)
5. [SSH Access to Raspberry Pi](#ssh-access-to-raspberry-pi)
6. [Troubleshooting](#troubleshooting)
7. [Setting Up ZeroTier on a New Raspberry Pi](#setting-up-zerotier-on-a-new-raspberry-pi)

---

## Prerequisites

Before starting, you need:
- A Mac or Windows laptop
- A ZeroTier account (free at https://my.zerotier.com)
- ZeroTier One installed on your computer
- Network authorization from the network administrator

---

## Network Information

**Network ID:** `2873fd00f2d70904`
**Network Name:** `my-first-network`
**Raspberry Pi ZeroTier IP:** `10.135.127.86`
**Raspberry Pi Username:** `nfetestpi2`

---

## Installing ZeroTier on Your Computer

### Mac:
1. Download ZeroTier One: https://www.zerotier.com/download/
2. Install it normally
3. After installation, the ZeroTier icon will appear in the top-right menu bar

### Windows:
1. Download ZeroTier from https://www.zerotier.com/download/
2. Install and launch it
3. ZeroTier icon will appear in the system tray

---

## Joining the Network

### Method 1: Using the ZeroTier Menu (Mac - Recommended)

1. Click the ZeroTier icon in your menu bar
2. You'll see "My Address:" with your device ID
3. Click on the network ID `2873fd00f2d70904` if it's already listed
4. Or select "Join New Network..." and enter: `2873fd00f2d70904`
5. The status will show "REQUESTING_CONFIGURATION"

### Method 2: Using Command Line

Mac/Linux:
```bash
sudo zerotier-cli join 2873fd00f2d70904
```

Windows (run as Administrator):
```cmd
zerotier-cli join 2873fd00f2d70904
```

### Authorization

After joining, you need to be authorized:

1. Contact the network administrator
2. Provide them with your device's MAC address or Device ID
3. They will authorize your device at https://my.zerotier.com
4. Once authorized, your device will receive an IP address like `10.135.127.xxx`

### Verify Connection

Mac/Linux:
```bash
sudo zerotier-cli listnetworks
```

You should see:
```
200 listnetworks 2873fd00f2d70904 my-first-network ... OK PRIVATE ... 10.135.127.xxx/24
```

The status should show **OK** and you should have an IP address assigned.

---

## SSH Access to Raspberry Pi

Once connected to the ZeroTier network, you can SSH to the Raspberry Pi:

```bash
ssh nfetestpi2@10.135.127.86
```

Enter the password when prompted.

**Note:** If you get a password prompt but it keeps failing, try using the `-v` flag for verbose output:
```bash
ssh -v nfetestpi2@10.135.127.86
```

### Optional: Set Up SSH Keys (Recommended)

To avoid entering passwords every time:

1. Generate SSH key on your computer (if you don't have one):
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

2. Copy your public key:
```bash
cat ~/.ssh/id_ed25519.pub
```

3. Add it to the Pi's authorized keys (via SSH or Raspberry Pi Connect):
```bash
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# Paste your public key, save and exit

# Set correct permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

4. Now you can SSH without a password:
```bash
ssh nfetestpi2@10.135.127.86
```

---

## Troubleshooting

### Issue: ZeroTier shows "REQUESTING_CONFIGURATION"

**Cause:** Your device hasn't been authorized on the network yet.

**Solution:**
1. Go to https://my.zerotier.com
2. Log in and navigate to network `2873fd00f2d70904`
3. Click "Member Devices" tab
4. Find your device and check the "Auth" checkbox

### Issue: ZeroTier shows "OFFLINE"

**Cause:** ZeroTier service isn't running properly.

**Solution for Mac:**
```bash
# Restart ZeroTier service
sudo launchctl unload /Library/LaunchDaemons/com.zerotier.one.plist
sudo launchctl load /Library/LaunchDaemons/com.zerotier.one.plist

# Verify it's online
sudo zerotier-cli info
```

You should see:
```
200 info <device-id> 1.16.0 ONLINE
```

**Solution for Windows:**
- Restart the ZeroTier service from Services (services.msc)
- Or restart the ZeroTier One application

### Issue: Can't ping or SSH to Raspberry Pi

**Symptoms:**
```bash
ping 10.135.127.86
# Shows: "No route to host" or "Request timeout"
```

**Solutions:**

1. **Check if ZeroTier is running on both devices:**
```bash
sudo zerotier-cli info
# Should show: ONLINE
```

2. **Verify both devices are on the same network:**
```bash
sudo zerotier-cli listnetworks
# Both should show network 2873fd00f2d70904 with status OK
```

3. **Try changing WiFi networks:**
Sometimes the initial WiFi network blocks ZeroTier's peer-to-peer connections. Try connecting to a different WiFi network or mobile hotspot.

4. **Check for RELAY connection:**
```bash
sudo zerotier-cli peers
```
If the Pi shows as "RELAY" instead of "DIRECT", there's a NAT traversal issue. Try:
- Restarting ZeroTier on both devices
- Leaving and rejoining the network
- Changing WiFi networks

5. **Restart ZeroTier on both devices:**

Mac:
```bash
sudo launchctl unload /Library/LaunchDaemons/com.zerotier.one.plist
sudo launchctl load /Library/LaunchDaemons/com.zerotier.one.plist
```

Raspberry Pi (via Raspberry Pi Connect):
```bash
sudo systemctl restart zerotier-one
```

6. **Leave old networks:**
If you have multiple networks joined, leave unused ones:
```bash
# List networks
sudo zerotier-cli listnetworks

# Leave old network
sudo zerotier-cli leave <old-network-id>
```

### Issue: SSH password keeps failing

**Solutions:**

1. Try verbose SSH to see what's happening:
```bash
ssh -v nfetestpi2@10.135.127.86
```

2. Make sure you're using the correct username (`nfetestpi2`, not `pi`)

3. Set up SSH keys instead (see SSH Keys section above)

---

## Setting Up ZeroTier on a New Raspberry Pi

If you need to set up ZeroTier on a new Raspberry Pi, follow these steps:

### Prerequisites
- Raspberry Pi with Raspberry Pi OS installed
- Internet connection
- Access to the Pi (via Raspberry Pi Connect, monitor/keyboard, or local SSH)

### Installation Steps

1. **Install ZeroTier on the Raspberry Pi:**
```bash
curl -s https://install.zerotier.com | sudo bash
```

2. **Join the network:**
```bash
sudo zerotier-cli join 2873fd00f2d70904
```

3. **Verify the Pi joined:**
```bash
sudo zerotier-cli listnetworks
```

You'll see status as "ACCESS_DENIED" initially.

4. **Authorize the Pi:**
- Go to https://my.zerotier.com
- Log in and navigate to network `2873fd00f2d70904`
- Click "Member Devices" tab
- Find the new Pi device (you can identify it by the MAC address or hostname)
- Check the "Auth" checkbox
- Note the "Managed IP" assigned to the Pi (e.g., `10.135.127.xxx`)

5. **Verify connection:**
```bash
sudo zerotier-cli listnetworks
```

Should now show:
```
200 listnetworks 2873fd00f2d70904 my-first-network ... OK PRIVATE ztxxxxxx 10.135.127.xxx/24
```

6. **Enable SSH (if not already enabled):**
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

7. **Make ZeroTier start on boot:**
```bash
sudo systemctl enable zerotier-one
```

8. **Test connection from another device:**
```bash
# From your computer (already on ZeroTier network)
ping <new-pi-ip>
ssh <username>@<new-pi-ip>
```

9. **Update this documentation** with the new Pi's IP address!

---

## Advanced: VNC Access (Remote Desktop)

If you need graphical access to the Raspberry Pi:

1. **Enable VNC on the Pi:**
```bash
sudo raspi-config
# Navigate to: Interface Options → VNC → Enable
```

2. **Install VNC Viewer on your computer:**
https://www.realvnc.com/en/connect/download/viewer/

3. **Connect using the ZeroTier IP:**
- Open VNC Viewer
- Enter: `10.135.127.86`
- Enter Pi username and password

---

## Contact

For network authorization or configuration issues, contact the network administrator.

**Network Management:** https://my.zerotier.com/network/2873fd00f2d70904

---

## Quick Reference

### Useful Commands

```bash
# Check ZeroTier status
sudo zerotier-cli info

# List joined networks
sudo zerotier-cli listnetworks

# Join a network
sudo zerotier-cli join <network-id>

# Leave a network
sudo zerotier-cli leave <network-id>

# Check peer connections
sudo zerotier-cli peers

# SSH to Raspberry Pi
ssh nfetestpi2@10.135.127.86
```

### Network Details
- **Network ID:** `2873fd00f2d70904`
- **Network Name:** `my-first-network`
- **Pi IP:** `10.135.127.86`
- **Pi Username:** `nfetestpi2`

---

*Last updated: 2026-03-28*
