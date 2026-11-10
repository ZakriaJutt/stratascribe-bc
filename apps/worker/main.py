"""Worker entry point: ``python -m worker [run|once|sweep|reconcile]``."""

from __future__ import annotations

import os
import socket
import sys
import time

from ai.llm import LlmClient
from ai.transcription import Transcriber
from core import config, jobs, retention
from core import logging as clog
from worker import handlers, providers

log = clog.get_logger("worker")


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def run_one(wid: str, asr: Transcriber, llm: LlmClient) -> bool:
    job = jobs.lease(wid, ("transcribe", "draft_minutes"))
    if job is None:
        return False
    token = clog.set_correlation_id(str(job.correlation_id))
    try:
        log.info("job leased", extra={"job_id": str(job.id), "job_kind": job.kind, "attempt": job.attempt})
        if job.kind == "transcribe":
            handlers.transcribe(job, asr)
        else:
            handlers.draft_minutes(job, llm)
        log.info("job succeeded", extra={"job_id": str(job.id), "job_kind": job.kind})
    except Exception as exc:  # noqa: BLE001 - any failure is recorded as an error code, never its text
        code = exc.code if isinstance(exc, handlers.PermanentError) else type(exc).__name__
        status = jobs.fail(job.id, code)
        log.warning("job failed", extra={"job_id": str(job.id), "job_kind": job.kind, "error_code": code,
                                          "status": status})
        if status == "failed":
            handlers.mark_failed(job)
    finally:
        clog.reset_correlation_id(token)
    return True


def drain(wid: str | None = None) -> int:
    wid = wid or worker_id()
    asr, llm = providers.transcriber(), providers.llm()
    n = 0
    while run_one(wid, asr, llm):
        n += 1
    return n


def loop() -> None:  # pragma: no cover - long-running
    wid = worker_id()
    cfg = config.settings()
    asr, llm = providers.transcriber(), providers.llm()
    last_beat = last_reconcile = 0.0
    log.info("worker started", extra={"worker_id": wid, "fingerprint": cfg.fingerprint()})
    while True:
        now = time.monotonic()
        if now - last_beat >= 30:
            jobs.heartbeat(wid, cfg.fingerprint())
            last_beat = now
        if now - last_reconcile >= 300:
            jobs.reconcile()
            last_reconcile = now
        if not run_one(wid, asr, llm):
            time.sleep(2)


def main(argv: list[str]) -> int:
    clog.configure()
    cmd = argv[1] if len(argv) > 1 else "run"
    config.settings()  # validate configuration first; exits with a clear message
    if cmd == "run":
        jobs.heartbeat(worker_id(), config.settings().fingerprint())
        loop()
    elif cmd == "once":
        jobs.heartbeat(worker_id(), config.settings().fingerprint())
        print(drain())
    elif cmd == "sweep":
        print(retention.sweep())
    elif cmd == "reconcile":
        print(jobs.reconcile())
    elif cmd == "heartbeat":
        jobs.heartbeat(worker_id(), config.settings().fingerprint())
    else:
        print("usage: python -m worker [run|once|sweep|reconcile|heartbeat]", file=sys.stderr)
        return 2
    return 0
