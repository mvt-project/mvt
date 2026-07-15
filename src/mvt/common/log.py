# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2025 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import threading
from contextvars import ContextVar, Token
from rich.console import Console
from rich.logging import RichHandler
from typing import Optional

INFO = logging.INFO
DEBUG = logging.DEBUG
ERROR = logging.ERROR
FATAL = logging.CRITICAL
WARNING = logging.WARNING

INFO_ALERT = 25
LOW_ALERT = 35
MEDIUM_ALERT = 45
HIGH_ALERT = 55
CRITICAL_ALERT = 65

logging.addLevelName(INFO_ALERT, "INFO")
logging.addLevelName(LOW_ALERT, "LOW")
logging.addLevelName(MEDIUM_ALERT, "MEDIUM")
logging.addLevelName(HIGH_ALERT, "HIGH")
logging.addLevelName(CRITICAL_ALERT, "CRITICAL")


_module_log_buffer: ContextVar[Optional[list[logging.LogRecord]]] = ContextVar(
    "mvt_module_log_buffer", default=None
)


def start_module_log_buffer() -> Token:
    """Capture console records in the current module execution context."""
    return _module_log_buffer.set([])


def finish_module_log_buffer(token: Token) -> list[logging.LogRecord]:
    records = _module_log_buffer.get() or []
    _module_log_buffer.reset(token)
    return records


class MVTLogHandler(RichHandler):
    def __init__(self, console: Optional[Console] = None, level: int = logging.DEBUG):
        super().__init__(console=console, level=level)
        self._console_lock = threading.RLock()

    def __add_prefix_space(self, level: str) -> str:
        max_length = len("CRITICAL ALERT")
        space = max_length - len(level)
        return f"{level}{' ' * space}"

    def _emit_record(self, record: logging.LogRecord) -> None:
        try:
            msg = rf"[grey50]\[{record.name}][/] {self.format(record)}"

            if record.levelno == ERROR:
                msg = f"[bold red]{self.__add_prefix_space('ERROR')}[/bold red] {msg}"
            elif record.levelno == FATAL:
                msg = f"[bold red]{self.__add_prefix_space('FATAL')}[/bold red] {msg}"
            elif record.levelno == WARNING:
                msg = f"[yellow]{self.__add_prefix_space('WARNING')}[/yellow] {msg}"
            elif record.levelno == INFO_ALERT:
                msg = f"[blue]{self.__add_prefix_space('INFO ALERT')}[/blue] {msg}"
            elif record.levelno == LOW_ALERT:
                msg = f"[yellow]{self.__add_prefix_space('LOW ALERT')}[/yellow] {msg}"
            elif record.levelno == MEDIUM_ALERT:
                msg = f"[sandy_brown]{self.__add_prefix_space('MEDIUM ALERT')}[/sandy_brown] {msg}"
            elif record.levelno == HIGH_ALERT:
                msg = f"[red]{self.__add_prefix_space('HIGH ALERT')}[/red] {msg}"
            elif record.levelno == CRITICAL_ALERT:
                msg = f"[bold red]{self.__add_prefix_space('CRITICAL ALERT')}[/bold red] {msg}"
            else:
                msg = f"{self.__add_prefix_space('')} {msg}"

            self.console.print(msg)

        except Exception:
            self.handleError(record)

    def emit(self, record: logging.LogRecord):
        buffer = _module_log_buffer.get()
        if buffer is not None:
            # More than one CLI can be imported in-process (notably in tests),
            # which can install multiple console handlers for the same record.
            if not buffer or buffer[-1] is not record:
                buffer.append(record)
            return

        with self._console_lock:
            self._emit_record(record)

    def emit_module_records(
        self, module_name: str, records: list[logging.LogRecord]
    ) -> None:
        """Print one module's captured records without interleaving."""
        with self._console_lock:
            self.console.print(f"[bold cyan]--- {module_name} ---[/bold cyan]")
            for record in records:
                self._emit_record(record)
