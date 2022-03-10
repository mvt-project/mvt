# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import io
import json
import tarfile
import zlib

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from mvt.common.utils import check_for_links, convert_timestamp_to_iso

PBKDF2_KEY_SIZE = 32


class AndroidBackupParsingError(Exception):
    """Exception raised file parsing an android backup file"""


class AndroidBackupNotImplemented(AndroidBackupParsingError):
    pass


class InvalidBackupPassword(AndroidBackupParsingError):
    pass


def to_utf8_bytes(input_bytes):
    output = []
    for byte in input_bytes:
        if byte < ord(b'\x80'):
            output.append(byte)
        else:
            output.append(ord('\xef') | (byte >> 12))
            output.append(ord('\xbc') | ((byte >> 6) & ord('\x3f')))
            output.append(ord('\x80') | (byte & ord('\x3f')))
    return bytes(output)


def parse_ab_header(data):
    """
    Parse the header of an Android Backup file
    Returns a dict {'backup': True, 'compression': False,
        'encryption': "none", 'version': 4}
    """
    if data.startswith(b"ANDROID BACKUP"):
        [magic_header, version, is_compressed, encryption, tar_data] = data.split(b"\n", 4)
        return {
            "backup": True,
            "compression": (is_compressed == b"1"),
            "version": int(version),
            "encryption": encryption.decode("utf-8")
        }

    return {
        "backup": False,
        "compression": None,
        "version": None,
        "encryption": None
    }


def decrypt_master_key(password, user_salt, user_iv, pbkdf2_rounds, master_key_blob, format_version, checksum_salt):
    """Generate AES key from user password uisng PBKDF2

    The backup master key is extracted from the master key blog after decryption.
    """
    # Derive key from password using PBKDF2
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=32, salt=user_salt, iterations=pbkdf2_rounds)
    key = kdf.derive(password.encode("utf-8"))

    # Decrypt master key blob
    cipher = Cipher(algorithms.AES(key), modes.CBC(user_iv))
    decryptor = cipher.decryptor()
    try:
        decryted_master_key_blob = decryptor.update(master_key_blob) + decryptor.finalize()

        # Extract key and IV from decrypted blob.
        key_blob = io.BytesIO(decryted_master_key_blob)
        master_iv_length = ord(key_blob.read(1))
        master_iv = key_blob.read(master_iv_length)

        master_key_length = ord(key_blob.read(1))
        master_key = key_blob.read(master_key_length)

        master_key_checksum_length = ord(key_blob.read(1))
        master_key_checksum = key_blob.read(master_key_checksum_length)
    except TypeError:
        raise InvalidBackupPassword()

    # Handle quirky encoding of master key bytes in Android original Java crypto code
    if format_version > 1:
        hmac_mk = to_utf8_bytes(master_key)
    else:
        hmac_mk = master_key

    # Derive checksum to confirm successful backup decryption.
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=32, salt=checksum_salt, iterations=pbkdf2_rounds)
    calculated_checksum = kdf.derive(hmac_mk)

    if master_key_checksum != calculated_checksum:
        raise InvalidBackupPassword()

    return master_key, master_iv


def decrypt_backup_data(encrypted_backup, password, encryption_algo, format_version):
    """
    Generate encryption keyffrom password and do decryption
    """
    if encryption_algo != b"AES-256":
        raise AndroidBackupNotImplemented("Encryption Algorithm not implemented")

    if password is None:
        raise InvalidBackupPassword()

    [user_salt, checksum_salt, pbkdf2_rounds, user_iv, master_key_blob, encrypted_data] = encrypted_backup.split(b"\n", 5)
    user_salt = bytes.fromhex(user_salt.decode("utf-8"))
    checksum_salt = bytes.fromhex(checksum_salt.decode("utf-8"))
    pbkdf2_rounds = int(pbkdf2_rounds)
    user_iv = bytes.fromhex(user_iv.decode("utf-8"))
    master_key_blob = bytes.fromhex(master_key_blob.decode("utf-8"))

    # Derive decryption master key from password
    master_key, master_iv = decrypt_master_key(password=password, user_salt=user_salt, user_iv=user_iv,
                                               pbkdf2_rounds=pbkdf2_rounds, master_key_blob=master_key_blob,
                                               format_version=format_version, checksum_salt=checksum_salt)

    # Decrypt and unpad backup data using derivied key
    cipher = Cipher(algorithms.AES(master_key), modes.CBC(master_iv))
    decryptor = cipher.decryptor()
    decrypted_tar = decryptor.update(encrypted_data) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(decrypted_tar)


def parse_backup_file(data, password=None):
    """
    Parse an ab file, returns a tar file
    """
    if not data.startswith(b"ANDROID BACKUP"):
        raise AndroidBackupParsingError("Invalid file header")

    [magic_header, version, is_compressed, encryption_algo, tar_data] = data.split(b"\n", 4)
    version = int(version)
    is_compressed = int(is_compressed)

    if encryption_algo != b"none":
        tar_data = decrypt_backup_data(tar_data, password, encryption_algo, format_version=version)

    if is_compressed:
        try:
            tar_data = zlib.decompress(tar_data)
        except zlib.error:
            raise AndroidBackupParsingError("Impossible to decompress the backup file")

    return tar_data


def parse_tar_for_sms(data):
    """
    Extract SMS from a tar backup archive
    Returns an array of SMS
    """
    dbytes = io.BytesIO(data)
    tar = tarfile.open(fileobj=dbytes)
    try:
        member = tar.getmember("apps/com.android.providers.telephony/d_f/000000_sms_backup")
    except KeyError:
        return []

    dhandler = tar.extractfile(member)
    return parse_sms_file(dhandler.read())


def parse_sms_file(data):
    """
    Parse an SMS file extracted from a folder
    Returns a list of SMS entries
    """
    res = []
    data = zlib.decompress(data)
    json_data = json.loads(data)

    for entry in json_data:
        message_links = check_for_links(entry["body"])
        utc_timestamp = datetime.datetime.utcfromtimestamp(int(entry["date"]) / 1000)
        entry["isodate"] = convert_timestamp_to_iso(utc_timestamp)
        entry["direction"] = ("sent" if int(entry["date_sent"]) else "received")

        # If we find links in the messages or if they are empty we add them to the list.
        if message_links or entry["body"].strip() == "":
            entry["links"] = message_links
            res.append(entry)

    return res
