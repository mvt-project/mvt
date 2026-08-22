# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from typing import Any

from .artifact import AndroidArtifact

SUSPICIOUS_MOUNT_POINTS = [
    "/system",
    "/vendor",
    "/product",
    "/system_ext",
]

SUSPICIOUS_OPTIONS = [
    "rw",
    "remount",
    "noatime",
    "nodiratime",
]

ALLOWLIST_NOATIME = [
    "/system_dlkm",
    "/system_ext",
    "/product",
    "/vendor",
    "/vendor_dlkm",
]


class Mounts(AndroidArtifact):
    """
    This artifact parses mount information from /proc/mounts or similar mount data.
    It can detect potentially suspicious mount configurations that may indicate
    a rooted or compromised device.
    """

    def parse(self, entry: str) -> None:
        """
        Parse mount information from the provided entry.

        Examples:
        /dev/block/bootdevice/by-name/system /system ext4 ro,seclabel,relatime 0 0
        /dev/block/dm-12 on / type ext4 (ro,seclabel,noatime)
        """
        self.results: list[dict[str, Any]] = []

        for line in entry.splitlines():
            line = line.strip()
            if not line:
                continue

            device = None
            mount_point = None
            filesystem_type = None
            mount_options = ""

            if " on " in line and " type " in line:
                try:
                    # Format: device on mount_point type filesystem_type (options)
                    device_part, rest = line.split(" on ", 1)
                    device = device_part.strip()

                    # Split by 'type' to get mount_point and filesystem info
                    mount_part, fs_part = rest.split(" type ", 1)
                    mount_point = mount_part.strip()

                    # Parse filesystem and options
                    if "(" in fs_part and fs_part.endswith(")"):
                        # Format: filesystem_type (options)
                        fs_and_opts = fs_part.strip()
                        paren_idx = fs_and_opts.find("(")
                        filesystem_type = fs_and_opts[:paren_idx].strip()
                        mount_options = fs_and_opts[paren_idx + 1 : -1].strip()
                    else:
                        # No options in parentheses, just filesystem type
                        filesystem_type = fs_part.strip()
                        mount_options = ""

                    # Skip if we don't have essential info
                    if not device or not mount_point or not filesystem_type:
                        continue

                    # Parse options into list
                    options_list = (
                        [opt.strip() for opt in mount_options.split(",") if opt.strip()]
                        if mount_options
                        else []
                    )

                    # Check if it's a system partition
                    is_system_partition = mount_point in SUSPICIOUS_MOUNT_POINTS or any(
                        mount_point.startswith(sp) for sp in SUSPICIOUS_MOUNT_POINTS
                    )

                    # Check if it's mounted read-write
                    is_read_write = "rw" in options_list

                    mount_entry = {
                        "device": device,
                        "mount_point": mount_point,
                        "filesystem_type": filesystem_type,
                        "mount_options": mount_options,
                        "options_list": options_list,
                        "is_system_partition": is_system_partition,
                        "is_read_write": is_read_write,
                    }

                    self.results.append(mount_entry)

                except ValueError:
                    # If parsing fails, skip this line
                    continue
            else:
                # Skip lines that don't match expected format
                continue

    @staticmethod
    def parse_mountinfo(entry: str, process_id: int) -> list[dict[str, Any]]:
        """Parse Linux /proc/PID/mountinfo records."""
        results = []
        for line in entry.splitlines():
            fields = line.split()
            if "-" not in fields:
                continue
            separator = fields.index("-")
            if separator < 6 or len(fields) < separator + 4:
                continue
            try:
                mount_id = int(fields[0])
                parent_id = int(fields[1])
            except ValueError:
                continue
            mount_options = fields[5].split(",")
            super_options = fields[separator + 3].split(",")
            options = list(dict.fromkeys(mount_options + super_options))
            mount_point = fields[4].replace("\\040", " ")
            device = fields[separator + 2].replace("\\040", " ")
            filesystem_type = fields[separator + 1]
            is_system = mount_point in SUSPICIOUS_MOUNT_POINTS or any(
                mount_point.startswith(f"{prefix}/")
                for prefix in SUSPICIOUS_MOUNT_POINTS
            )
            results.append(
                {
                    "mount_id": mount_id,
                    "parent_id": parent_id,
                    "major_minor": fields[2],
                    "root": fields[3].replace("\\040", " "),
                    "mount_point": mount_point,
                    "device": device,
                    "filesystem_type": filesystem_type,
                    "mount_options": ",".join(options),
                    "options_list": options,
                    "optional_fields": fields[6:separator],
                    "is_system_partition": is_system,
                    "is_read_write": "rw" in options,
                    "process_ids": [process_id],
                }
            )
        return results

    def check_indicators(self) -> None:
        """
        Check for suspicious mount configurations that may indicate root access
        or other security concerns.
        """
        system_rw_mounts = []
        suspicious_mounts = []

        for mount in self.results:
            mount_point = mount["mount_point"]
            options = mount["options_list"]

            # Check for system partitions mounted as read-write
            if mount["is_system_partition"] and mount["is_read_write"]:
                system_rw_mounts.append(mount)
                if mount_point == "/system":
                    self.alertstore.high(
                        "Root detected /system partition is mounted as read-write (rw)",
                        "",
                        mount,
                    )
                else:
                    self.alertstore.high(
                        f"System partition {mount_point} is mounted as read-write (rw). This may indicate system modifications.",
                        "",
                        mount,
                    )

            # Check for other suspicious mount options
            suspicious_opts = [opt for opt in options if opt in SUSPICIOUS_OPTIONS]
            if suspicious_opts and mount["is_system_partition"]:
                if (
                    "noatime" in mount["mount_options"]
                    and mount["mount_point"] in ALLOWLIST_NOATIME
                ):
                    continue
                suspicious_mounts.append(mount)
                self.alertstore.medium(
                    f"Suspicious mount options found for {mount_point}: {', '.join(suspicious_opts)}",
                    "",
                    mount,
                )

            # Log interesting mount information
            if mount_point == "/data" or mount_point.startswith("/sdcard"):
                self.log.info(
                    "Data partition: %s mounted as %s with options: %s",
                    mount_point,
                    mount["filesystem_type"],
                    mount["mount_options"],
                )

        self.log.info("Parsed %d mount entries", len(self.results))

        # Check indicators if available
        if not self.indicators:
            return

        for mount in self.results:
            # Check if any mount points match indicators
            ioc = self.indicators.check_file_path(mount.get("mount_point", ""))
            if ioc:
                self.alertstore.critical(
                    ioc.message,
                    "",
                    mount,
                    matched_indicator=ioc.ioc,
                )

            # Check device paths for indicators
            ioc = self.indicators.check_file_path(mount.get("device", ""))
            if ioc:
                self.alertstore.critical(
                    ioc.message,
                    "",
                    mount,
                    matched_indicator=ioc.ioc,
                )
