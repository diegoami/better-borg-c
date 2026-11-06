#!/usr/bin/env python3
"""Build native Borg and reject incomplete/failing numeric test summaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def check_summaries(output):
    clean = ANSI.sub("", output)
    totals = [(int(a), int(b)) for a, b in re.findall(r"^Total:[ \t]+(\d+)/(\d+)(?:[ \t]+passed[^\n]*)?[ \t]*$", clean, re.MULTILINE)]
    # alltests runs the unit gate first and the test frontend gate second.
    # The original runners can return zero even when assertions fail.
    if len(totals) != 2:
        raise ValueError("Expected exactly two numerical unit/frontend summaries")
    for name, (passed, total), minimum in zip(("unit", "frontend"), totals, (965, 5)):
        if total < minimum or passed != total:
            raise ValueError(f"Incomplete or failing {name} gate: {passed}/{total}; minimum {minimum}")
    return {name: {"passed": p, "total": n} for name, (p, n) in zip(("unit", "frontend"), totals)}


def run(command, log, env):
    print("Running:", " ".join(command), flush=True)
    with log.open("w") as saved:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            saved.write(line)
            saved.flush()
            print(line, end="", flush=True)
        code = process.wait()
    if code:
        raise RuntimeError(f"Command failed with exit {code}; see {log}")
    return log.read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    artifacts = ROOT / "artifacts/native"
    artifacts.mkdir(parents=True, exist_ok=True)
    build = ROOT / "build/native"
    env = os.environ.copy()
    # These knobs change coverage/path semantics; use the declared self-contained profile.
    env.pop("FORCE_PATH", None)
    env.pop("VERBOSE", None)
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"
    result = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "profile": "Borg + X11 + test frontend; self-contained", "success": False}
    try:
        run(["cmake", "-S", str(ROOT), "-B", str(build), "-DSUPPORT_BORG=ON",
             "-DSUPPORT_TEST_FRONTEND=ON", "-DSUPPORT_X11_FRONTEND=ON"], artifacts / "configure.log", env)
        run(["cmake", "--build", str(build), "--parallel", str(args.jobs)], artifacts / "build.log", env)
        output = run(["cmake", "--build", str(build), "--target", "alltests", "--parallel", str(args.jobs)],
                     artifacts / "alltests.log", env)
        result["summaries"] = check_summaries(output)
        result["success"] = True
    except (RuntimeError, ValueError) as exc:
        result["error"] = str(exc)
        print(str(exc), file=sys.stderr)
    finally:
        result["logs"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts.glob("*.log")}
        (artifacts / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
