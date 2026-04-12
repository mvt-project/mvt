# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import binascii
import glob
import logging
import os
import os.path
import plistlib
import shutil
import sqlite3
import tempfile
from typing import Optional

from iphone_backup_decrypt import EncryptedBackup
from iphone_backup_decrypt import google_iphone_dataprotection

log = logging.getLogger(__name__)

# Import pbkdf2_hmac from the same source iphone_backup_decrypt uses internally,
# so our key derivation is consistent with theirs.
try:
    from fastpbkdf2 import pbkdf2_hmac
except ImportError:
    import Crypto.Hash.SHA1
    import Crypto.Hash.SHA256
    import Crypto.Protocol.KDF

    _HASH_FNS = {"sha1": Crypto.Hash.SHA1, "sha256": Crypto.Hash.SHA256}

    def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
        return Crypto.Protocol.KDF.PBKDF2(
            password, salt, dklen, iterations, hmac_hash_module=_HASH_FNS[hash_name]
        )


class MVTEncryptedBackup(EncryptedBackup):
    """Extends EncryptedBackup with derived key export/import.

    NOTE: This subclass relies on internal APIs of iphone_backup_decrypt
    (specifically _read_and_unlock_keybag, _keybag, and the Keybag class
    internals). Pinned to iphone_backup_decrypt==0.9.0.
    """

    def __init__(self, *, backup_directory, passphrase=None, derived_key=None):
        if passphrase:
            super().__init__(backup_directory=backup_directory, passphrase=passphrase)
            self._derived_key = None  # Will be set after keybag unlock
        elif derived_key:
            self._init_without_passphrase(backup_directory, derived_key)
        else:
            raise ValueError("Either passphrase or derived_key must be provided")

    def _init_without_passphrase(self, backup_directory, derived_key):
        """Replicate parent __init__ state without requiring a passphrase."""
        self.decrypted = False
        self._backup_directory = os.path.expandvars(backup_directory)
        self._passphrase = None
        self._manifest_plist_path = os.path.join(
            self._backup_directory, "Manifest.plist"
        )
        self._manifest_plist = None
        self._manifest_db_path = os.path.join(self._backup_directory, "Manifest.db")
        self._keybag = None
        self._unlocked = False
        self._temporary_folder = tempfile.mkdtemp()
        self._temp_decrypted_manifest_db_path = os.path.join(
            self._temporary_folder, "Manifest.db"
        )
        self._temp_manifest_db_conn = None
        self._derived_key = derived_key  # 32 raw bytes

    def _read_and_unlock_keybag(self):
        """Override to capture derived key on password unlock, or use
        a pre-derived key to skip PBKDF2."""
        if self._unlocked:
            return self._unlocked

        with open(self._manifest_plist_path, "rb") as infile:
            self._manifest_plist = plistlib.load(infile)
        self._keybag = google_iphone_dataprotection.Keybag(
            self._manifest_plist["BackupKeyBag"]
        )

        if self._derived_key:
            # Skip PBKDF2, unwrap class keys directly with pre-derived key
            self._unlocked = _unlock_keybag_with_derived_key(
                self._keybag, self._derived_key
            )
        else:
            # Normal path: full PBKDF2 derivation, capturing the intermediate key
            self._unlocked, self._derived_key = _unlock_keybag_and_capture_key(
                self._keybag, self._passphrase
            )
            self._passphrase = None

        if not self._unlocked:
            raise ValueError("Failed to decrypt keys: incorrect passphrase?")
        return True

    def get_decryption_key(self):
        """Return derived key as hex string (64 chars / 32 bytes)."""
        if self._derived_key is None:
            raise ValueError("No derived key available")
        return self._derived_key.hex()


def _unlock_keybag_with_derived_key(keybag, passphrase_key):
    """Unlock keybag class keys using a pre-derived passphrase_key,
    skipping the expensive PBKDF2 rounds."""
    WRAP_PASSPHRASE = 2
    for classkey in keybag.classKeys.values():
        if b"WPKY" not in classkey:
            continue
        if classkey[b"WRAP"] & WRAP_PASSPHRASE:
            k = google_iphone_dataprotection._AESUnwrap(
                passphrase_key, classkey[b"WPKY"]
            )
            if not k:
                return False
            classkey[b"KEY"] = k
    return True


def _unlock_keybag_and_capture_key(keybag, passphrase):
    """Run full PBKDF2 key derivation and AES unwrap, returning
    (success, passphrase_key) so the derived key can be exported."""
    passphrase_round1 = pbkdf2_hmac(
        "sha256", passphrase, keybag.attrs[b"DPSL"], keybag.attrs[b"DPIC"], 32
    )
    passphrase_key = pbkdf2_hmac(
        "sha1", passphrase_round1, keybag.attrs[b"SALT"], keybag.attrs[b"ITER"], 32
    )
    WRAP_PASSPHRASE = 2
    for classkey in keybag.classKeys.values():
        if b"WPKY" not in classkey:
            continue
        if classkey[b"WRAP"] & WRAP_PASSPHRASE:
            k = google_iphone_dataprotection._AESUnwrap(
                passphrase_key, classkey[b"WPKY"]
            )
            if not k:
                return False, None
            classkey[b"KEY"] = k
    return True, passphrase_key


class DecryptBackup:
    """This class provides functions to decrypt an encrypted iTunes backup
    using either a password or a key file.


    """

    def __init__(self, backup_path: str, dest_path: Optional[str] = None) -> None:
        """Decrypts an encrypted iOS backup.
        :param backup_path: Path to the encrypted backup folder
        :param dest_path: Path to the folder where to store the decrypted backup
        """
        self.backup_path = os.path.abspath(backup_path)
        self.dest_path = dest_path
        self._backup = None
        self._decryption_key = None

    def can_process(self) -> bool:
        return self._backup is not None

    @staticmethod
    def is_encrypted(backup_path: str) -> bool:
        """Query Manifest.db file to see if it's encrypted or not.

        :param backup_path: Path to the backup to decrypt

        """
        conn = sqlite3.connect(os.path.join(backup_path, "Manifest.db"))
        cur = conn.cursor()
        try:
            cur.execute("SELECT fileID FROM Files LIMIT 1;")
        except sqlite3.DatabaseError:
            return True
        else:
            log.critical("The backup does not seem encrypted!")
            return False

    def process_backup(self) -> None:
        if not os.path.exists(self.dest_path):
            os.makedirs(self.dest_path)

        manifest_path = os.path.join(self.dest_path, "Manifest.db")
        # Extract a decrypted Manifest.db to the destination folder.
        self._backup.save_manifest_file(output_filename=manifest_path)

        # Iterate over all files in the backup and decrypt them,
        # preserving the XX/file_id directory structure that downstream
        # modules expect.
        with self._backup.manifest_db_cursor() as cur:
            cur.execute(
                "SELECT fileID, domain, relativePath, file FROM Files WHERE flags=1"
            )
            for file_id, domain, relative_path, file_bplist in cur:
                # This may be a partial backup. Skip files from the manifest
                # which do not exist locally.
                source_file_path = os.path.join(
                    self.backup_path, file_id[:2], file_id
                )
                if not os.path.exists(source_file_path):
                    log.debug(
                        "Skipping file %s. File not found in encrypted backup directory.",
                        source_file_path,
                    )
                    continue

                item_folder = os.path.join(self.dest_path, file_id[:2])
                os.makedirs(item_folder, exist_ok=True)

                try:
                    decrypted = self._backup._decrypt_inner_file(
                        file_id=file_id, file_bplist=file_bplist
                    )
                    with open(
                        os.path.join(item_folder, file_id), "wb"
                    ) as handle:
                        handle.write(decrypted)
                    log.info(
                        "Decrypted file %s [%s] to %s/%s",
                        relative_path,
                        domain,
                        item_folder,
                        file_id,
                    )
                except Exception as exc:
                    log.error("Failed to decrypt file %s: %s", relative_path, exc)

        # Copying over the root plist files as well.
        for file_name in os.listdir(self.backup_path):
            if file_name.endswith(".plist"):
                log.info("Copied plist file %s to %s", file_name, self.dest_path)
                shutil.copy(os.path.join(self.backup_path, file_name), self.dest_path)

    def decrypt_with_password(self, password: str) -> None:
        """Decrypts an encrypted iOS backup.

        :param password: Password to use to decrypt the original backup

        """
        log.info("Decrypting iOS backup at path %s with password", self.backup_path)

        if not os.path.exists(os.path.join(self.backup_path, "Manifest.plist")):
            possible = glob.glob(os.path.join(self.backup_path, "*", "Manifest.plist"))

            if len(possible) == 1:
                newpath = os.path.dirname(possible[0])
                log.warning(
                    "No Manifest.plist in %s, using %s instead.",
                    self.backup_path,
                    newpath,
                )
                self.backup_path = newpath
            elif len(possible) > 1:
                log.critical(
                    "No Manifest.plist in %s, and %d Manifest.plist files in subdirs. "
                    "Please choose one!",
                    self.backup_path,
                    len(possible),
                )
                return

        # Before proceeding, we check whether the backup is indeed encrypted.
        if not self.is_encrypted(self.backup_path):
            return

        try:
            self._backup = MVTEncryptedBackup(
                backup_directory=self.backup_path,
                passphrase=password,
            )
            # Eagerly trigger keybag unlock so wrong-password errors
            # surface here rather than later during process_backup().
            self._backup.test_decryption()
        except Exception as exc:
            self._backup = None
            if (
                isinstance(exc, ValueError)
                and "passphrase" in str(exc).lower()
            ):
                log.critical("Failed to decrypt backup. Password is probably wrong.")
            elif (
                isinstance(exc, FileNotFoundError)
                and hasattr(exc, "filename")
                and os.path.basename(exc.filename) == "Manifest.plist"
            ):
                log.critical(
                    "Failed to find a valid backup at %s. "
                    "Did you point to the right backup path?",
                    self.backup_path,
                )
            else:
                log.exception(exc)
                log.critical(
                    "Failed to decrypt backup. Did you provide the correct password? "
                    "Did you point to the right backup path?"
                )

    def decrypt_with_key_file(self, key_file: str) -> None:
        """Decrypts an encrypted iOS backup using a key file.

        :param key_file: File to read the key bytes to decrypt the backup

        """
        log.info(
            "Decrypting iOS backup at path %s with key file %s",
            self.backup_path,
            key_file,
        )

        # Before proceeding, we check whether the backup is indeed encrypted.
        if not self.is_encrypted(self.backup_path):
            return

        with open(key_file, "rb") as handle:
            key_bytes = handle.read()

        # Key should be 64 hex encoded characters (32 raw bytes)
        if len(key_bytes) != 64:
            log.critical(
                "Invalid key from key file. Did you provide the correct key file?"
            )
            return

        try:
            key_bytes_raw = binascii.unhexlify(key_bytes)
            self._backup = MVTEncryptedBackup(
                backup_directory=self.backup_path,
                derived_key=key_bytes_raw,
            )
            # Eagerly trigger keybag unlock so wrong-key errors surface here.
            self._backup.test_decryption()
        except Exception as exc:
            self._backup = None
            log.exception(exc)
            log.critical(
                "Failed to decrypt backup. Did you provide the correct key file?"
            )

    def get_key(self) -> None:
        """Retrieve and prints the encryption key."""
        if not self._backup:
            return

        self._decryption_key = self._backup.get_decryption_key()
        log.info(
            'Derived decryption key for backup at path %s is: "%s"',
            self.backup_path,
            self._decryption_key,
        )

    def write_key(self, key_path: str) -> None:
        """Save extracted key to file.

        :param key_path: Path to the file where to write the derived decryption
                         key.

        """
        if not self._decryption_key:
            return

        try:
            with open(key_path, "w", encoding="utf-8") as handle:
                handle.write(self._decryption_key)
        except Exception as exc:
            log.exception(exc)
            log.critical("Failed to write key to file: %s", key_path)
            return
        else:
            log.info(
                "Wrote decryption key to file: %s. This file is "
                "equivalent to a plaintext password. Keep it safe!",
                key_path,
            )
