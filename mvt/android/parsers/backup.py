# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import zlib
import json
import tarfile
import hashlib
import datetime
import pyaes
from mvt.common.utils import check_for_links, convert_timestamp_to_iso


PBKDF2_KEY_SIZE = 32


class AndroidBackupParseError(Exception):
    """Exception raised file parsing an android backup file"""


class AndroidBackupNotImplemented(AndroidBackupParseError):
    pass


class InvalidBackupPassword(AndroidBackupParseError):
    pass


def decrypt_master_key_blob(key, aes_iv, cipher_text):
    """
    Decrypt the master key blob with AES
    From : https://github.com/FloatingOctothorpe/dump_android_backup
    """

    aes = pyaes.AESModeOfOperationCBC(key, aes_iv)

    plain_text = b''
    while len(plain_text) < len(cipher_text):
        offset = len(plain_text)
        plain_text += aes.decrypt(cipher_text[offset:(offset + 16)])

    blob = io.BytesIO(plain_text)
    master_iv_length = ord(blob.read(1))
    master_iv = blob.read(master_iv_length)
    master_key_length = ord(blob.read(1))
    master_key = blob.read(master_key_length)
    master_key_checksum_length = ord(blob.read(1))
    master_key_checksum = blob.read(master_key_checksum_length)

    return master_iv, master_key, master_key_checksum


def to_utf8_bytes(input_bytes):
    """Emulate bytes being converted into a "UTF8 byte array"
    For more info see the Bouncy Castle Crypto package Strings.toUTF8ByteArray
    method:
      https://github.com/bcgit/bc-java/blob/master/core/src/main/java/org/bouncycastle/util/Strings.java#L142
    From https://github.com/FloatingOctothorpe/dump_android_backup
    """
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
    Inspired by https://github.com/FloatingOctothorpe/dump_android_backup
    """
    if not data.startswith(b"ANDROID BACKUP"):
        raise AndroidBackupParseError("Invalid file header")

    [magic_header, version, is_compressed, encryption, tar_data] = data.split(b"\n", 4)
    version = int(version)
    is_compressed = int(is_compressed)
    if is_compressed == 1:
        raise AndroidBackupNotImplemented("Compression is not implemented")

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

        key = hashlib.pbkdf2_hmac('sha1',
                                  password.encode('utf-8'),
                                  user_salt,
                                  pbkdf2_rounds,
                                  PBKDF2_KEY_SIZE)
        try:
            [master_iv, master_key, master_key_checksum] = decrypt_master_key_blob(key, user_iv, master_key_blob)
        except TypeError:
            raise InvalidBackupPassword()

        if version > 1:
            hmac_mk = to_utf8_bytes(master_key)
        else:
            hmac_mk = master_key

        calculated_checksum = hashlib.pbkdf2_hmac('sha1',
                                                  hmac_mk,
                                                  checksum_salt,
                                                  pbkdf2_rounds,
                                                  PBKDF2_KEY_SIZE)

        if  master_key_checksum != calculated_checksum:
            raise InvalidBackupPassword()

        decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(master_key, master_iv))
        tar_data = decrypter.feed(encrypted_data)

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
