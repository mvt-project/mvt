# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import logging
import plistlib
import threading
from pathlib import Path

import pytest
from Crypto.Cipher import AES
from iphone_backup_decrypt import IncorrectPassphraseError

from mvt.ios.decrypt import DecryptBackup, MVTEncryptedBackup


def _encrypted_file(backup_path, file_id, key, plaintext):
    padding_length = AES.block_size - (len(plaintext) % AES.block_size)
    padded = plaintext + bytes([padding_length]) * padding_length
    encrypted = AES.new(key, AES.MODE_CBC, iv=b"\x00" * AES.block_size).encrypt(
        padded
    )
    source_path = backup_path / file_id[:2] / file_id
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(encrypted)


def _keybag_tlv(tag, value):
    return tag + len(value).to_bytes(4, "big") + value


def test_derived_key_can_unlock_keybag(mocker, tmp_path, caplog):
    password = b"backup password"
    salt = b"salt" * 4
    dpsl = b"dpsl" * 4
    round1 = hashlib.pbkdf2_hmac("sha256", password, dpsl, 1, 32)
    derived_key = hashlib.pbkdf2_hmac("sha1", round1, salt, 1, 32)
    wrapped_class_key = AES.new(derived_key, AES.MODE_KW).seal(b"k" * 32)
    keybag_data = b"".join(
        [
            _keybag_tlv(b"TYPE", (1).to_bytes(4, "big")),
            _keybag_tlv(b"DPSL", dpsl),
            _keybag_tlv(b"DPIC", (1).to_bytes(4, "big")),
            _keybag_tlv(b"SALT", salt),
            _keybag_tlv(b"ITER", (1).to_bytes(4, "big")),
            _keybag_tlv(b"UUID", b"g" * 16),
            _keybag_tlv(b"WRAP", (2).to_bytes(4, "big")),
            _keybag_tlv(b"UUID", b"c" * 16),
            _keybag_tlv(b"CLAS", (1).to_bytes(4, "big")),
            _keybag_tlv(b"WRAP", (2).to_bytes(4, "big")),
            _keybag_tlv(b"WPKY", wrapped_class_key),
        ]
    )
    (tmp_path / "Manifest.plist").write_bytes(
        plistlib.dumps({"IsEncrypted": True, "BackupKeyBag": keybag_data})
    )
    (tmp_path / "Manifest.db").touch()

    with pytest.raises(IncorrectPassphraseError):
        MVTEncryptedBackup(
            backup_directory=str(tmp_path), passphrase="wrong"
        )._read_and_unlock_keybag()

    password_backup = MVTEncryptedBackup(
        backup_directory=str(tmp_path), passphrase=password
    )
    password_backup._read_and_unlock_keybag()
    assert password_backup.get_decryption_key() == derived_key.hex()

    key_backup = MVTEncryptedBackup(
        backup_directory=str(tmp_path), passphrase_key=derived_key
    )
    key_backup._read_and_unlock_keybag()
    assert key_backup.get_decryption_key() == derived_key.hex()

    # Exercise MVT's password and key-file entry points with the native unlock.
    mocker.patch.object(DecryptBackup, "is_encrypted", return_value=True)
    mocker.patch.object(
        MVTEncryptedBackup,
        "test_decryption",
        MVTEncryptedBackup._read_and_unlock_keybag,
    )
    password_decryptor = DecryptBackup(str(tmp_path))
    password_decryptor.decrypt_with_password(password)
    password_decryptor.get_key()
    assert password_decryptor._decryption_key == derived_key.hex()

    key_file = tmp_path / "key.txt"
    key_file.write_text(derived_key.hex())
    key_decryptor = DecryptBackup(str(tmp_path))
    key_decryptor.decrypt_with_key_file(str(key_file))
    assert key_decryptor.can_process()
    assert key_decryptor._backup.get_decryption_key() == derived_key.hex()

    with caplog.at_level(logging.CRITICAL, logger="mvt.ios.decrypt"):
        wrong_password = DecryptBackup(str(tmp_path))
        wrong_password.decrypt_with_password("wrong")
    assert not wrong_password.can_process()
    assert "Password is probably wrong" in caplog.text


def test_invalid_backup_folder_uses_specific_error(tmp_path, caplog):
    decryptor = DecryptBackup(str(tmp_path))
    with caplog.at_level(logging.CRITICAL, logger="mvt.ios.decrypt"):
        decryptor.decrypt_with_password("password")

    assert not decryptor.can_process()
    assert "Failed to find a valid backup" in caplog.text


def test_extract_file_by_id_preserves_bytes_with_wrong_manifest_size(
    mocker, tmp_path
):
    file_id = "ab" + "1" * 38
    plaintext = b"complete decrypted content"
    inner_key = b"k" * 32
    _encrypted_file(tmp_path, file_id, inner_key, plaintext)

    file_plist = mocker.Mock(
        encryption_key=b"wrapped-key",
        protection_class=1,
        filesize=1,
        mtime=None,
    )
    mocker.patch("mvt.ios.decrypt.FilePlist", return_value=file_plist)
    (tmp_path / "Manifest.plist").touch()
    (tmp_path / "Manifest.db").touch()

    backup = MVTEncryptedBackup(
        backup_directory=str(tmp_path), passphrase_key=b"d" * 32
    )
    mocker.patch.object(backup, "_read_and_unlock_keybag", return_value=True)
    backup.keybag = mocker.Mock()
    backup.keybag.unwrap_key_for_class.return_value = inner_key
    streaming_decrypt = mocker.spy(backup, "_decrypt_file_to_disk")
    output_path = tmp_path / "output"

    backup.extract_file_by_id(
        file_id=file_id,
        file_bplist=b"plist",
        output_filename=str(output_path),
    )

    assert output_path.read_bytes() == plaintext
    streaming_decrypt.assert_called_once()
    backup.keybag.unwrap_key_for_class.assert_called_once_with(
        protection_class=1, wrapped_file_key=b"wrapped-key"
    )


def test_extract_file_by_id_copies_unencrypted_files(mocker, tmp_path):
    file_id = "cd" + "2" * 38
    source_path = tmp_path / file_id[:2] / file_id
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"plain content")

    file_plist = mocker.Mock(encryption_key=None)
    mocker.patch("mvt.ios.decrypt.FilePlist", return_value=file_plist)
    (tmp_path / "Manifest.plist").touch()
    (tmp_path / "Manifest.db").touch()
    backup = MVTEncryptedBackup(
        backup_directory=str(tmp_path), passphrase_key=b"d" * 32
    )
    mocker.patch.object(backup, "_read_and_unlock_keybag", return_value=True)
    output_path = tmp_path / "output"

    backup.extract_file_by_id(
        file_id=file_id,
        file_bplist=b"plist",
        output_filename=str(output_path),
    )

    assert output_path.read_bytes() == b"plain content"


def test_get_decryption_key_uses_unlocked_keybag(tmp_path):
    (tmp_path / "Manifest.plist").touch()
    (tmp_path / "Manifest.db").touch()
    backup = MVTEncryptedBackup(
        backup_directory=str(tmp_path), passphrase_key=b"d" * 32
    )
    with pytest.raises(ValueError, match="No derived key available"):
        backup.get_decryption_key()

    backup.keybag = type("Keybag", (), {"passphrase_key": b"d" * 32})()
    assert backup.get_decryption_key() == "64" * 32


@pytest.mark.parametrize("with_symlink", [False, True], ids=["file-id", "symlink"])
def test_process_backup_rejects_unsafe_file_ids_and_destinations(
    mocker, tmp_path, with_symlink
):
    backup_path = tmp_path / "backup"
    destination = tmp_path / "destination"
    outside = tmp_path / "outside"
    backup_path.mkdir()
    destination.mkdir()
    outside.mkdir()

    safe_file_id = "ef" + "3" * 38
    unsafe_file_id = "../../outside-file"
    symlink_file_id = "ab" + "4" * 38
    file_ids = [safe_file_id]
    if with_symlink:
        file_ids.append(symlink_file_id)
    for file_id in file_ids:
        source_path = backup_path / file_id[:2] / file_id
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(b"encrypted")
    if with_symlink:
        try:
            (destination / "ab").symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("creating symbolic links is not permitted on this system")

    cursor = mocker.MagicMock()
    records = [
        (safe_file_id, "Domain", "safe", b"plist"),
        (unsafe_file_id, "Domain", "unsafe", b"plist"),
    ]
    if with_symlink:
        records.append((symlink_file_id, "Domain", "symlink", b"plist"))
    cursor.__iter__.return_value = iter(records)
    cursor_context = mocker.MagicMock()
    cursor_context.__enter__.return_value = cursor

    backup = mocker.MagicMock()
    backup.manifest_db_cursor.return_value = cursor_context

    def extract_file_by_id(*, output_filename, **kwargs):
        Path(output_filename).write_bytes(b"decrypted")

    backup.extract_file_by_id.side_effect = extract_file_by_id
    decryptor = DecryptBackup(
        str(backup_path), str(destination), max_workers=1
    )
    decryptor._backup = backup

    decryptor.process_backup()

    assert (destination / safe_file_id[:2] / safe_file_id).read_bytes() == b"decrypted"
    if with_symlink:
        assert not (outside / symlink_file_id).exists()
    backup.extract_file_by_id.assert_called_once()
    assert backup.extract_file_by_id.call_args.kwargs["file_id"] == safe_file_id


def test_process_backup_decrypts_files_concurrently(mocker, tmp_path):
    backup_path = tmp_path / "backup"
    destination = tmp_path / "destination"
    backup_path.mkdir()

    file_ids = ["ab" + "1" * 38, "cd" + "2" * 38]
    for file_id in file_ids:
        source_path = backup_path / file_id[:2] / file_id
        source_path.parent.mkdir()
        source_path.write_bytes(b"encrypted")

    cursor = mocker.MagicMock()
    cursor.__iter__.return_value = iter(
        (file_id, "Domain", file_id, b"plist") for file_id in file_ids
    )
    cursor_context = mocker.MagicMock()
    cursor_context.__enter__.return_value = cursor

    barrier = threading.Barrier(2)
    backup = mocker.MagicMock()
    backup.manifest_db_cursor.return_value = cursor_context

    def extract_file_by_id(*, file_id, output_filename, **kwargs):
        barrier.wait(timeout=5)
        Path(output_filename).write_bytes(file_id.encode())

    backup.extract_file_by_id.side_effect = extract_file_by_id
    decryptor = DecryptBackup(str(backup_path), str(destination), max_workers=2)
    decryptor._backup = backup

    decryptor.process_backup()

    for file_id in file_ids:
        assert (destination / file_id[:2] / file_id).read_bytes() == file_id.encode()


def test_process_backup_logs_worker_errors(mocker, tmp_path, caplog):
    backup_path = tmp_path / "backup"
    destination = tmp_path / "destination"
    backup_path.mkdir()
    file_id = "ef" + "3" * 38
    source_path = backup_path / file_id[:2] / file_id
    source_path.parent.mkdir()
    source_path.write_bytes(b"encrypted")

    cursor = mocker.MagicMock()
    cursor.__iter__.return_value = iter([(file_id, "Domain", "failing-file", b"plist")])
    cursor_context = mocker.MagicMock()
    cursor_context.__enter__.return_value = cursor

    backup = mocker.MagicMock()
    backup.manifest_db_cursor.return_value = cursor_context
    backup.extract_file_by_id.side_effect = ValueError("broken file")
    decryptor = DecryptBackup(str(backup_path), str(destination))
    decryptor._backup = backup

    with caplog.at_level(logging.ERROR, logger="mvt.ios.decrypt"):
        decryptor.process_backup()

    assert "Failed to decrypt file failing-file: broken file" in caplog.text
