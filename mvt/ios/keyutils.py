import os
import logging
from iOSbackup import iOSbackup

log = logging.getLogger(__name__)

class KeyUtils:
    """This class provides functions to extract a backup key from a password.
    """

    def __init__(self, password, backup_path):
        """Generates a key file for an iOS backup.
        :param password: Backup encryption password
        :param key_file: Path to the file where to store the generated key file
        """
        self.password = password
        self.backup_path = backup_path
        self._backup = None

    def get_key(self):
        try:
            self._backup = iOSbackup(udid=os.path.basename(self.backup_path),
                                     cleartextpassword=self.password,
                                     backuproot=os.path.dirname(self.backup_path))
        except Exception as e:
            log.exception(e)
            log.critical("Failed to decrypt backup. Did you provide the correct password?")
            return
        else:
            self.decryption_key = self._backup.getDecryptionKey()
            log.info("Extracted decryption key.")

    def print_key(self):
        self.get_key()
        log.info("Decryption key for backup at path %s is:\n %s",
                 self.backup_path, self.decryption_key)
    
    def write_key(self, key_file):
        self.get_key()
        
        try:
            with open(key_file, 'w') as writer:
                writer.write(self.decryption_key)
        except Exception as e:
            log.exception(e)
            log.critical("Failed to write key file.")
            return
        else:
            log.info("Wrote decryption key for backup at path %s to file %s",
                     self.backup_path, key_file)
            log.warn("The file %s is equivalent to a plaintext password. Keep this file safe!",
                     key_file)
