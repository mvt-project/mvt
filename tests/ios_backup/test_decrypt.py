# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import threading
from pathlib import Path

from Crypto.Cipher import AES

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

    backup = MVTEncryptedBackup(
        backup_directory=str(tmp_path), derived_key=b"d" * 32
    )
    mocker.patch.object(backup, "_read_and_unlock_keybag", return_value=True)
    backup._keybag = mocker.Mock()
    backup._keybag.unwrapKeyForClass.return_value = inner_key
    streaming_decrypt = mocker.spy(backup, "_decrypt_file_to_disk")
    output_path = tmp_path / "output"

    backup.extract_file_by_id(
        file_id=file_id,
        file_bplist=b"plist",
        output_filename=str(output_path),
    )

    assert output_path.read_bytes() == plaintext
    streaming_decrypt.assert_called_once()


def test_extract_file_by_id_copies_unencrypted_files(mocker, tmp_path):
    file_id = "cd" + "2" * 38
    source_path = tmp_path / file_id[:2] / file_id
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"plain content")

    file_plist = mocker.Mock(encryption_key=None)
    mocker.patch("mvt.ios.decrypt.FilePlist", return_value=file_plist)
    backup = MVTEncryptedBackup(
        backup_directory=str(tmp_path), derived_key=b"d" * 32
    )
    mocker.patch.object(backup, "_read_and_unlock_keybag", return_value=True)
    output_path = tmp_path / "output"

    backup.extract_file_by_id(
        file_id=file_id,
        file_bplist=b"plist",
        output_filename=str(output_path),
    )

    assert output_path.read_bytes() == b"plain content"


def test_process_backup_rejects_unsafe_file_ids_and_destinations(mocker, tmp_path):
    backup_path = tmp_path / "backup"
    destination = tmp_path / "destination"
    outside = tmp_path / "outside"
    backup_path.mkdir()
    destination.mkdir()
    outside.mkdir()

    safe_file_id = "ef" + "3" * 38
    unsafe_file_id = "../../outside-file"
    symlink_file_id = "ab" + "4" * 38
    for file_id in (safe_file_id, symlink_file_id):
        source_path = backup_path / file_id[:2] / file_id
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(b"encrypted")
    (destination / "ab").symlink_to(outside, target_is_directory=True)

    cursor = mocker.MagicMock()
    cursor.__iter__.return_value = iter(
        [
            (safe_file_id, "Domain", "safe", b"plist"),
            (unsafe_file_id, "Domain", "unsafe", b"plist"),
            (symlink_file_id, "Domain", "symlink", b"plist"),
        ]
    )
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
