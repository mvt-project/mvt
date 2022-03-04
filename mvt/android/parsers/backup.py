# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import zlib
import json
import tarfile
import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
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


def parse_sms_backup(data, password=None):
    """
    Parse a backup file and returns SMS in it
    """
    tardata = parse_backup_file(data, password=password)
    return parse_tar_for_sms(tardata)


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


def parse_backup_file(data, password=None):
    """
    Parse an ab file, returns a tar file
    """
    if not data.startswith(b"ANDROID BACKUP"):
        raise AndroidBackupParsingError("Invalid file header")

    [magic_header, version, is_compressed, encryption, tar_data] = data.split(b"\n", 4)
    version = int(version)
    is_compressed = int(is_compressed)

    if encryption != b"none":
        if encryption != b"AES-256":
            raise AndroidBackupNotImplemented("Encryption Algorithm not implemented")
        if password is None:
            raise InvalidBackupPassword()
        [user_salt, checksum_salt, pbkdf2_rounds, user_iv, master_key_blob, encrypted_data] = tar_data.split(b"\n", 5)
        user_salt = bytes.fromhex(user_salt.decode("utf-8"))
        checksum_salt = bytes.fromhex(checksum_salt.decode("utf-8"))
        pbkdf2_rounds = int(pbkdf2_rounds)
        user_iv = bytes.fromhex(user_iv.decode("utf-8"))
        master_key_blob = bytes.fromhex(master_key_blob.decode("utf-8"))

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=32,
            salt=user_salt,
            iterations=pbkdf2_rounds)
        key = kdf.derive(password.encode("utf-8"))

        cipher = Cipher(algorithms.AES(key), modes.CBC(user_iv))
        decryptor = cipher.decryptor()
        try:
            plain_text = decryptor.update(master_key_blob) + decryptor.finalize()

            blob = io.BytesIO(plain_text)
            master_iv_length = ord(blob.read(1))
            master_iv = blob.read(master_iv_length)
            master_key_length = ord(blob.read(1))
            master_key = blob.read(master_key_length)
            master_key_checksum_length = ord(blob.read(1))
            master_key_checksum = blob.read(master_key_checksum_length)
        except TypeError:
            raise InvalidBackupPassword()

        if version > 1:
            hmac_mk = to_utf8_bytes(master_key)
        else:
            hmac_mk = master_key

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=32,
            salt=checksum_salt,
            iterations=pbkdf2_rounds)
        calculated_checksum = kdf.derive(hmac_mk)

        if  master_key_checksum != calculated_checksum:
            raise InvalidBackupPassword()

        cipher = Cipher(algorithms.AES(master_key), modes.CBC(master_iv))
        decryptor = cipher.decryptor()
        tar_data = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        tar_data = data = unpadder.update(tar_data)

    if is_compressed == 1:
        try:
            tar_data = zlib.decompress(tar_data)
        except zlib.error:
            raise AndroidBackupParsingError("Impossible to decompress the file")

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
