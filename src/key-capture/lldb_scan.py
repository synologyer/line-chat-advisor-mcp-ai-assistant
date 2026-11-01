"""LLDB command that writes possible 32-hex LINE DB keys to a mode-0600 file.

The command never prints candidate values. The companion validator must delete
the output file after testing the candidates against a read-only DB snapshot.
"""

import json
import os
import re
import time

import lldb


ASCII_HEX = re.compile(rb"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32}(?![0-9A-Fa-f])")
UTF16_HEX = re.compile(rb"(?:(?:[0-9A-Fa-f]\x00){32})")
CHUNK_SIZE = 1024 * 1024
OVERLAP = 4096
MAX_CANDIDATES = 10_000
MAX_SCAN_SECONDS = 30
MAX_SCAN_BYTES = 256 * 1024 * 1024


def _candidate_values(data: bytes):
    for match in ASCII_HEX.finditer(data):
        yield match.group(0).decode("ascii").lower()
    for match in UTF16_HEX.finditer(data):
        yield match.group(0)[::2].decode("ascii").lower()


def line_scan(debugger, _command, result, _internal_dict):
    output_path = os.environ.get("LINE_KEY_CANDIDATES_PATH")
    status_path = os.environ.get("LINE_KEY_SCAN_STATUS_PATH")
    if not output_path or not status_path:
        result.SetError("Required output paths are unavailable.")
        return

    process = debugger.GetSelectedTarget().GetProcess()
    if not process.IsValid():
        result.SetError("No valid process is attached.")
        return

    candidates = set()
    regions_scanned = 0
    bytes_scanned = 0
    address = 0
    deadline = time.monotonic() + MAX_SCAN_SECONDS
    max_address = (1 << 64) - 1
    # Enumerate before reading: prioritize small allocations rather than spending
    # the entire budget in a large reserved/mostly-empty mapping.
    plan = []
    while address < max_address and time.monotonic() < deadline:
        region = lldb.SBMemoryRegionInfo()
        error = process.GetMemoryRegionInfo(address, region)
        if not error.Success():
            break
        start = region.GetRegionBase()
        end = region.GetRegionEnd()
        if end <= address:
            break
        if region.IsReadable() and region.IsWritable():
            plan.append((end - start, start, end))
        address = end
    for _, start, end in sorted(plan):
        if time.monotonic() >= deadline or bytes_scanned >= MAX_SCAN_BYTES or len(candidates) >= MAX_CANDIDATES:
            break
        regions_scanned += 1
        cursor = start
        # Bound each region so a huge mapping cannot starve other allocations.
        region_end = min(end, start + 8 * 1024 * 1024)
        tail = b""
        while cursor < region_end and len(candidates) < MAX_CANDIDATES and time.monotonic() < deadline and bytes_scanned < MAX_SCAN_BYTES:
            amount = min(CHUNK_SIZE, region_end - cursor, MAX_SCAN_BYTES - bytes_scanned)
            read_error = lldb.SBError()
            block = process.ReadMemory(cursor, amount, read_error)
            if read_error.Success() and block:
                combined = tail + block
                candidates.update(_candidate_values(combined))
                bytes_scanned += len(block)
                tail = combined[-OVERLAP:]
            else:
                tail = b""
            cursor += amount

    old_umask = os.umask(0o077)
    try:
        with open(output_path, "w", encoding="ascii") as handle:
            for candidate in sorted(candidates):
                handle.write(candidate + "\n")
        with open(status_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "candidateCount": len(candidates),
                    "regionsScanned": regions_scanned,
                    "bytesScanned": bytes_scanned,
                    "candidateLimitReached": len(candidates) >= MAX_CANDIDATES,
                    "timeLimitReached": time.monotonic() >= deadline,
                    "byteLimitReached": bytes_scanned >= MAX_SCAN_BYTES,
                },
                handle,
            )
    finally:
        os.umask(old_umask)
    result.AppendMessage("LINE key candidate scan completed without printing candidate material.")


def __lldb_init_module(debugger, _internal_dict):
    debugger.HandleCommand("command script add -f lldb_scan.line_scan line_scan")
