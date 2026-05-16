# Complete iOS Guide for MVT

This guide walks you through analyzing an iOS device backup with MVT, including using Indicators of Compromise (IOCs) to detect known spyware.

---

## Step 1: Create an iOS Backup

You have two options to create a backup:

### Option A: Using Finder (macOS - Recommended)

1. Connect your iPhone to your Mac using a USB/Lightning cable
2. Open **Finder**
3. Select your iPhone from the sidebar (under "Locations")
4. In the **General** tab, check **"Encrypt local backup"** (important: encrypted backups contain more forensic data)
5. Click **"Back Up Now"**
6. Wait for the backup to complete (may take 10-30 minutes)

**Backup Location:** `~/Library/Application Support/MobileSync/Backup/`

You'll see a folder named with your device's UDID (a long string of letters/numbers).

### Option B: Using libimobiledevice (Command Line)

If you have `libimobiledevice` installed:

```bash
# Enable encryption (recommended)
idevicebackup2 -i encryption on

# Create a full backup
idevicebackup2 backup --full /path/to/backup/
```

---

## Step 2: Analyze the Backup

### If Your Backup is Encrypted

First, decrypt it:

```bash
# Decrypt the backup (MVT will prompt for password)
mvt-ios decrypt-backup -d ~/decrypted-backup ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID-FOLDER]

# Or provide password via environment variable
MVT_IOS_BACKUP_PASSWORD="yourpassword" mvt-ios decrypt-backup -d ~/decrypted-backup ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID-FOLDER]
```

### Run the Analysis

```bash
# Basic analysis (saves results to a folder)
mvt-ios check-backup --output ~/mvt-results ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID-FOLDER]

# Or if you decrypted it:
mvt-ios check-backup --output ~/mvt-results ~/decrypted-backup
```

**What this does:**
- Extracts artifacts from the backup (SMS, calls, Safari history, installed apps, etc.)
- Creates JSON files in `~/mvt-results/` with all extracted data
- Shows progress and findings in the terminal

---

## Step 3: Using Indicators of Compromise (IOCs)

IOCs are known signatures of spyware and malicious activity. MVT can check your backup against these indicators.

### 3.1 Download Public IOCs

MVT can automatically download the latest public indicators:

```bash
mvt-ios download-iocs
```

This downloads indicators from the [mvt-indicators repository](https://github.com/mvt-project/mvt-indicators) and stores them locally. These will be **automatically loaded** when you run analysis commands.

**What gets downloaded:**
- Known spyware indicators (Pegasus, Predator, etc.)
- Malicious domains, URLs, and file hashes
- Suspicious app IDs and configuration profiles

### 3.2 Analyze Backup WITH IOCs

Once you've downloaded IOCs, they're automatically used:

```bash
# Analyze backup with auto-loaded IOCs
mvt-ios check-backup --output ~/mvt-results ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID-FOLDER]
```

**What happens:**
- MVT extracts all data from the backup
- Compares it against downloaded IOCs
- **Highlights any matches** in the terminal (in red/yellow)
- Creates `*_detected.json` files in the output folder for any matches

### 3.3 Use Custom IOCs

You can also use your own IOC files:

```bash
# Use a specific IOC file
mvt-ios check-backup --iocs ~/path/to/custom-iocs.stix2 --output ~/mvt-results ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID-FOLDER]

# Use multiple IOC files
mvt-ios check-backup --iocs ~/iocs/pegasus.stix2 --iocs ~/iocs/predator.stix2 --output ~/mvt-results ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID-FOLDER]
```

### 3.4 Check Existing Results Against IOCs

If you already have analysis results, you can check them against IOCs:

```bash
# Check previously saved results
mvt-ios check-iocs --iocs ~/path/to/iocs.stix2 ~/mvt-results
```

### 3.5 Where to Get IOCs

**Public IOCs:**
- **Amnesty International investigations:**
  - [Pegasus IOCs](https://raw.githubusercontent.com/AmnestyTech/investigations/master/2021-07-18_nso/pegasus.stix2)
  - [Predator IOCs](https://raw.githubusercontent.com/AmnestyTech/investigations/master/2021-12-16_cytrox/cytrox.stix2)
- **MVT Indicators Repository:** Automatically downloaded with `download-iocs`
- **Stalkerware Indicators:** [GitHub](https://github.com/Te-k/stalkerware-indicators)

**Download a specific IOC file:**
```bash
# Download Pegasus IOCs
curl -o ~/pegasus.stix2 https://raw.githubusercontent.com/AmnestyTech/investigations/master/2021-07-18_nso/pegasus.stix2

# Use it
mvt-ios check-backup --iocs ~/pegasus.stix2 --output ~/mvt-results ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID-FOLDER]
```

---

## Complete Example Workflow

Here's a complete example from start to finish:

```bash
# 1. Download latest IOCs
mvt-ios download-iocs

# 2. Find your backup (replace UDID with your actual folder name)
ls ~/Library/Application\ Support/MobileSync/Backup/

# 3. If encrypted, decrypt it first
mvt-ios decrypt-backup -d ~/decrypted-backup ~/Library/Application\ Support/MobileSync/Backup/[YOUR-UDID]

# 4. Analyze with IOCs (they're auto-loaded after download-iocs)
mvt-ios check-backup --output ~/mvt-results ~/decrypted-backup

# 5. Review the results
ls ~/mvt-results/
# Look for files ending in "_detected.json" - these contain matches!
```

---

## Understanding the Results

### Output Files

After analysis, you'll find JSON files in your output folder:

- `*.json` - All extracted data (SMS, calls, Safari history, etc.)
- `*_detected.json` - **Only suspicious findings** that matched IOCs
- `*.txt` - Timeline files (chronological view of events)

### What to Look For

**In the terminal output:**
- **Red/Yellow warnings** = Potential matches found
- Look for messages like "Found suspicious indicator" or "Detected IOC match"

**In the JSON files:**
- Open `*_detected.json` files to see what was flagged
- Check the timeline files for chronological context

### Important Notes

⚠️ **Public IOCs are not comprehensive:**
- They may miss recent or unknown spyware
- A "clean" result doesn't guarantee the device is safe
- For serious concerns, seek expert forensic assistance

---

## Quick Reference Commands

```bash
# Download IOCs
mvt-ios download-iocs

# Decrypt backup
mvt-ios decrypt-backup -d [output] [encrypted-backup]

# Analyze backup (with auto-loaded IOCs)
mvt-ios check-backup --output [output-folder] [backup-folder]

# Analyze with custom IOCs
mvt-ios check-backup --iocs [ioc-file] --output [output-folder] [backup-folder]

# Check existing results against IOCs
mvt-ios check-iocs --iocs [ioc-file] [results-folder]

# Get help for any command
mvt-ios [command] --help
```

---

## Troubleshooting

**"Backup is encrypted" error:**
- Use `decrypt-backup` command first
- Or provide password: `MVT_IOS_BACKUP_PASSWORD="password" mvt-ios check-backup ...`

**"No indicators found" message:**
- Run `mvt-ios download-iocs` first
- Or manually specify IOCs with `--iocs` flag

**Can't find backup folder:**
- Default location: `~/Library/Application Support/MobileSync/Backup/`
- List backups: `ls ~/Library/Application\ Support/MobileSync/Backup/`

---

## Additional Resources

- **Full Documentation:** https://docs.mvt.re/
- **GitHub Repository:** https://github.com/mvt-project/mvt
- **Amnesty Security Lab:** https://securitylab.amnesty.org/get-help/

