# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
# https://license.mvt.re/1.1/

"""Password prompts with masked keyboard feedback.

This is based on the ``echo_char`` support added to :mod:`getpass` in Python
3.14. MVT supports Python 3.10 and later, so it cannot use that API directly.
"""

import contextlib
import io
import os
import sys
import warnings
from typing import TextIO


def prompt_password(prompt: str) -> str:
    """Return a password while displaying an asterisk for each character."""
    try:
        import termios

        return _unix_getpass(prompt, termios)
    except ImportError:
        try:
            import msvcrt

            return _windows_getpass(prompt, msvcrt)
        except ImportError:
            return _fallback_getpass(prompt)


def _unix_getpass(prompt: str, termios) -> str:
    password = None
    input_stream: TextIO
    output_stream: TextIO
    with contextlib.ExitStack() as stack:
        try:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
            tty = io.FileIO(fd, "w+")
            stack.enter_context(tty)
            input_stream = io.TextIOWrapper(tty)
            stack.enter_context(input_stream)
            output_stream = input_stream
        except OSError:
            stack.close()
            try:
                fd = sys.stdin.fileno()
            except (AttributeError, ValueError):
                return _fallback_getpass(prompt)
            input_stream = sys.stdin
            output_stream = sys.stderr

        try:
            old = termios.tcgetattr(fd)
            new = old[:]
            new[3] &= ~termios.ECHO
            new[3] &= ~termios.ICANON
            try:
                termios.tcsetattr(fd, termios.TCSAFLUSH, new)
                password = _readline_with_asterisks(output_stream, input_stream, prompt)
            finally:
                termios.tcsetattr(fd, termios.TCSAFLUSH, old)
                output_stream.flush()
        except termios.error:
            if password is not None:
                raise
            password = _fallback_getpass(prompt)

        output_stream.write("\n")
        return password


def _windows_getpass(prompt: str, msvcrt) -> str:
    if sys.stdin is not sys.__stdin__:
        return _fallback_getpass(prompt)

    for char in prompt:
        msvcrt.putwch(char)

    password = ""
    while True:
        char = msvcrt.getwch()
        if char in ("\r", "\n"):
            break
        if char == "\x03":
            raise KeyboardInterrupt
        if char == "\b":
            if password:
                msvcrt.putwch("\b")
                msvcrt.putwch(" ")
                msvcrt.putwch("\b")
            password = password[:-1]
        else:
            password += char
            msvcrt.putwch("*")

    msvcrt.putwch("\r")
    msvcrt.putwch("\n")
    return password


def _fallback_getpass(prompt: str) -> str:
    warnings.warn(
        "Can not control echo on the terminal.",
        category=UserWarning,
        stacklevel=2,
    )
    print("Warning: Password input may be echoed.", file=sys.stderr)
    return input(prompt)


def _readline_with_asterisks(
    output_stream: TextIO, input_stream: TextIO, prompt: str
) -> str:
    output_stream.write(prompt)
    output_stream.flush()

    password = ""
    eof_pressed = False
    while True:
        char = input_stream.read(1)
        if char in ("\n", "\r"):
            break
        if char == "\x03":
            raise KeyboardInterrupt
        if char in ("\x7f", "\b"):
            if password:
                output_stream.write("\b \b")
                output_stream.flush()
            password = password[:-1]
        elif char == "\x04":
            if eof_pressed:
                break
            eof_pressed = True
        elif char != "\x00":
            password += char
            output_stream.write("*")
            output_stream.flush()
            eof_pressed = False
    return password
