"""Shared collection logic for TA-psi scripted inputs (PSI pressure files)."""
import json
import os
import re
import sys

PRESSURE = "/proc/pressure"
RESOURCES = ("cpu", "memory", "io")
PREFIX = {"cpu": "cpu", "memory": "mem", "io": "io"}
FIELDS = (
    "some_avg10",
    "some_avg60",
    "some_avg300",
    "full_avg10",
    "full_avg60",
    "full_avg300",
    "total_ms",
)

LINE_RE = re.compile(r"^(some|full) avg10=([\d.]+) avg60=([\d.]+) avg300=([\d.]+) total=([\d.]+)")

USEC_PER_MSEC = 1000.0


def read_file(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ms(x):
    v = _num(x)
    return None if v is None else v / USEC_PER_MSEC


def parse_pressure(path):
    text = read_file(path)
    if text is None:
        return None
    rec = {}
    for line in text.splitlines():
        m = LINE_RE.match(line.strip())
        if not m:
            continue
        tag, a10, a60, a300, total = m.groups()
        if tag == "some":
            rec["some_avg10"] = _num(a10)
            rec["some_avg60"] = _num(a60)
            rec["some_avg300"] = _num(a300)
            rec["total_ms"] = _ms(total)
        else:
            rec["full_avg10"] = _num(a10)
            rec["full_avg60"] = _num(a60)
            rec["full_avg300"] = _num(a300)
    for f in FIELDS:
        if rec.get(f) is None:
            return None
    return rec


def discover():
    data = {}
    for res in RESOURCES:
        rec = parse_pressure(os.path.join(PRESSURE, res))
        if rec is not None:
            data[res] = rec
    if not data:
        return {"status": "unsupported"}
    status = "ok"
    for res, rec in data.items():
        if (rec.get("some_avg10") or 0.0) > 25.0:
            status = "alarm"
            break
    data["status"] = status
    return data


def metrics_payload(data):
    payload = {}
    if not isinstance(data, dict):
        return payload
    for res in RESOURCES:
        rec = data.get(res)
        if not isinstance(rec, dict):
            continue
        prefix = PREFIX[res]
        for f in FIELDS:
            v = rec.get(f)
            if v is None:
                continue
            payload["psi_%s_%s" % (prefix, f)] = round(v, 1) if f == "total_ms" else round(v, 4)
    return payload


def emit(payload):
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stdout.flush()


def fail(message):
    sys.stderr.write("TA-psi collection error: %s\n" % message)
    return 1
