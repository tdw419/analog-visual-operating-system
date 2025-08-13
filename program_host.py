#!/usr/bin/env python3
"""
PXOS Program Host
-----------------
The master tool for managing the PXOS program ecosystem.
Features:
- Program discovery across multiple roots.
- Comprehensive validation with manifest, signature, and performance checks.
- A submission ritual to a central program registry.
- CLI scaffolding for new programs and plugins.
"""
import argparse
import os
import re
import sys
import glob
import json
import time
import ast
import inspect
import traceback
import importlib.util
from datetime import datetime
from pathlib import Path
from types import ModuleType
from textwrap import shorten
from typing import Dict, List, Any, Optional, Tuple
from statistics import mean, quantiles

try:
    import yaml # Requires PyYAML for manifest validation
except ImportError:
    yaml = None

import hashlib
import tempfile
import shutil
from filelock import FileLock, Timeout

# === Constants & Templates ===
DEFAULT_ROOTS = ["programs", "examples", "plugins"]
PROGRAM_INDEX = "program_index.json"
MANIFEST_SUFFIX = "_manifest.yaml"
PERF_THRESHOLD_MS = 5.0 # Default warning threshold for update()

PROGRAM_TEMPLATE = """\
\"\"\"PXOS Program: {name}
Hooks:
  - setup(ctx): One-time initialization
  - update(ctx, dt): Per-frame update
  - on_event(ctx, ev): Optional event handler
\"\"\"
def setup(ctx):
    \"\"\"Initialize regions and state.\"\"\"
    ctx.log("setup: hello from {name}")
    helper = getattr(ctx, "add_osc_filter_scope_default", None)
    if helper and not hasattr(ctx, "_initialized_{slug}"):
        helper("{slug}", x=80, y=80)
        ctx._initialized_{slug} = True
    ctx.phase = 0.0

def update(ctx, dt):
    \"\"\"Update parameters per frame.\"\"\"
    ctx.phase = (ctx.phase + dt) % 1.0
    sp = getattr(ctx, "set_param", None)
    if sp:
        sp("{slug}_osc", "freq", 0.5 + 0.5 * ctx.phase)
    if ctx.frame() % 120 == 0:
        pu = getattr(ctx, "pulse", None)
        if pu:
            pu("{slug}_scope", duration=12)

def on_event(ctx, ev):
    \"\"\"Handle click events.\"\"\"
    if ev.get("type") == "click":
        jit = getattr(ctx, "jitter", None)
        if jit:
            jit(ev["x"], ev["y"])
            ctx.log(f"[{name}] click @ ({{ev['x']}},{{ev['y']}})")
"""

PLUGIN_TEMPLATE = """\
\"\"\"PXOS Plugin: {name}
Wave interference pattern with multiple oscillators.
Hooks:
  - setup(ctx): Initializes two oscillators and a scope
  - update(ctx, dt): Updates interference pattern
  - on_event(ctx, ev): Adjusts oscillator positions on click
\"\"\"
def setup(ctx):
    \"\"\"Initialize two oscillators and a scope for interference.\"\"\"
    ctx.log("setup: {name}")
    helper = getattr(ctx, "add_osc_filter_scope_default", None)
    if helper and not hasattr(ctx, "_initialized_{slug}"):
        helper("{slug}_1", x=80, y=80)
        helper("{slug}_2", x=120, y=80)
        ctx.add_connection("{slug}_1_osc", "out", "{slug}_2_filter", "in", cyclic=True)
        ctx._initialized_{slug} = True
    ctx.phase_1 = 0.0
    ctx.phase_2 = 0.0

def update(ctx, dt):
    \"\"\"Update interference pattern.\"\"\"
    ctx.phase_1 = (ctx.phase_1 + dt) % 1.0
    ctx.phase_2 = (ctx.phase_2 + dt * 1.1) % 1.0
    sp = getattr(ctx, "set_param", None)
    if sp:
        sp("{slug}_1_osc", "freq", 0.5 + 0.5 * ctx.phase_1)
        sp("{slug}_2_osc", "freq", 0.5 + 0.5 * ctx.phase_2)
    if ctx.frame() % 120 == 0:
        pu = getattr(ctx, "pulse", None)
        if pu:
            pu("{slug}_1_scope", duration=12)
            pu("{slug}_2_scope", duration=12)

def on_event(ctx, ev):
    \"\"\"Adjust oscillator positions on click.\"\"\"
    if ev.get("type") == "click":
        jit = getattr(ctx, "jitter", None)
        if jit:
            jit(ev["x"], ev["y"])
            ctx.log(f"[{name}] click @ ({{ev['x']}},{{ev['y']}})")
"""

MANIFEST_TEMPLATE = """\
name: {name}
author: Your Name
description: A brief description of your program's functionality
version: 1.0.0
requirements:
  - python>=3.8
  - pxos>=1.0
tags: []
"""

# === Program Discovery ===
def _iter_program_files(roots=DEFAULT_ROOTS):
    for root in roots:
        p = Path(root)
        if not p.exists():
            continue
        for fp in p.rglob("*.py"):
            if fp.name.startswith("_") or fp.name == "__init__.py":
                continue
            yield fp

def _ast_metadata(py_path: Path):
    try:
        src = py_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"read_error: {e}"}
    try:
        tree = ast.parse(src, filename=str(py_path))
        doc = ast.get_docstring(tree) or ""
        funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        return {
            "doc": doc.strip(),
            "has_setup": "setup" in funcs,
            "has_update": "update" in funcs,
            "has_on_event": "on_event" in funcs,
            "loc": len(src.splitlines()),
            "error": None,
            "func_nodes": funcs,
        }
    except SyntaxError as e:
        return {"error": f"syntax_error: line {e.lineno} {e.msg}"}

def _load_manifest(program_path: Path) -> tuple[Optional[Dict[str, Any]], List[str]]:
    manifest_path = program_path.parent / f"{program_path.stem}_manifest.yaml"
    errors = []
    if not manifest_path.exists():
        return None, [f"Missing manifest: {manifest_path}"]
    if not yaml:
        return None, ["PyYAML not installed, cannot read manifest"]
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return None, [f"Invalid YAML in manifest: {e}"]
    required_fields = ["name", "description", "version"]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required manifest field: {field}")
    if manifest.get("name") != program_path.stem:
        errors.append(f"Manifest name '{manifest.get('name')}' does not match file name '{program_path.stem}'")
    return manifest, errors

def list_programs(roots=DEFAULT_ROOTS):
    rows = []
    for fp in _iter_program_files(roots):
        meta = _ast_metadata(fp)
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(fp.stat().st_mtime))
        manifest, manifest_errors = _load_manifest(fp)
        desc = meta.get("doc") or "No docstring"
        author = "Unknown"
        version = "Unknown"
        tags = []
        if manifest:
            desc = manifest.get("description", desc)
            author = manifest.get("author", "Unknown")
            version = manifest.get("version", "1.0.0")
            tags = manifest.get("tags", [])
        row = {
            "path": str(fp),
            "name": fp.stem,
            "mtime": mtime,
            "hooks": "".join([
                "S" if meta.get("has_setup") else "-",
                "U" if meta.get("has_update") else "-",
                "E" if meta.get("has_on_event") else "-",
            ]) if not meta.get("error") else "ERR",
            "description": shorten(desc.replace("\n", " "), width=80, placeholder="…"),
            "author": author,
            "version": version,
            "tags": tags,
            "error": meta.get("error"),
            "loc": meta.get("loc"),
        }
        rows.append(row)

    # Pretty print
    if not rows:
        print("❌ No programs found in examples/, programs/, or plugins/")
        return
    print(f"{'Hooks':4} {'LOC':>4} {'Modified':19} {'Author':20} {'Path'}")
    print("-"*100)
    for r in rows:
        hooks = r["hooks"]
        loc = f"{r.get('loc') or 0:>4}" if hooks != "ERR" else " -"
        print(f"{hooks:4} {loc} {r['mtime']:19} {r['author'][:19]:<20} {r['path']}")
        if r["error"]:
            print(f" ERR: {r['error']}")
        else:
            print(f" {r['description']}")
            if r["tags"]:
                print(f" Tags: {', '.join(r['tags'])}")

    # Write program_index.json
    Path("program_index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("\n📜 Wrote program_index.json")

# === Atomic Index Operations ===
INDEX_PATH = Path("programs") / "program_index.json"
INDEX_LOCK = Path("programs") / ".program_index.lock"
INDEX_TIMEOUT_SEC = 8

def _sha256_of_text(txt: str) -> str:
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16]

def _sha256(path: str) -> str:
    """Calculate SHA256 checksum of a file"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _read_json_safe(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Corrupted or partial—rename aside and start fresh
        bad = path.with_suffix(".corrupted.json")
        try:
            path.rename(bad)
        except Exception:
            pass
        return []

def _write_json_atomic(path: Path, payload: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tf:
        json.dump(payload, tf, indent=2)
        tf.flush()
        os.fsync(tf.fileno())
        tmp_name = tf.name
    os.replace(tmp_name, path)

def update_program_index(entry: dict, index_path: Path = INDEX_PATH, lock_path: Path = INDEX_LOCK):
    """
    Atomically merge/update `entry` into program_index.json under a file lock.
    Keys used for identity:
      - `name` (required)
      - `path` (preferred) or `version` as tie-breaker
    """
    lock = FileLock(str(lock_path))
    try:
        with lock.acquire(timeout=INDEX_TIMEOUT_SEC):
            index = _read_json_safe(index_path)
            # replace prior entry for same program
            def same(e):
                if e.get("path") and entry.get("path"):
                    return e["path"] == entry["path"]
                if e.get("name") == entry.get("name"):
                    # fallback: name + version
                    return e.get("version") == entry.get("version")
                return False

            index = [e for e in index if not same(e)]
            index.append(entry)
            # keep stable ordering by name then version
            index.sort(key=lambda e: (e.get("name",""), e.get("version","")))
            _write_json_atomic(index_path, index)
    except Timeout:
        print("⚠️ program_index.json lock timeout—skipping index update.")

# === Program Validation ===
REQ_SIGS = {
    "setup": ("ctx",),
    "update": ("ctx", "dt"),
    "on_event": ("ctx", "ev"),  # optional hook, but if present must match
}

def _check_hook_signature(mod: ModuleType, name: str, required: bool = True):
    """
    Enforce exact parameter names/arity for PXOS hooks.
    Returns (ok: bool, err: Optional[str])
    """
    fn = getattr(mod, name, None)
    if fn is None:
        return (not required), (f"missing {name}()" if required else None)
    if not callable(fn):
        return False, f"{name} is not callable"
    try:
        sig = inspect.signature(fn)
        params = tuple(p.name for p in sig.parameters.values()
                       if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD))
        if params != REQ_SIGS[name]:
            expected = ", ".join(REQ_SIGS[name])
            return False, f"{name} signature must be {name}({expected})"
        return True, None
    except Exception as e:
        return False, f"{name} signature check failed: {e}"

def _validate_manifest_for(py_path: Path):
    """
    Looks for sidecar manifest `{stem}_manifest.yaml` next to the program.
    Returns (ok: bool, manifest: dict|None, err: str|None)
    """
    mpath = py_path.with_name(f"{py_path.stem}_manifest.yaml")
    if not mpath.exists():
        return False, None, f"manifest missing: {mpath.name}"
    if yaml is None:
        return False, None, "PyYAML not available to parse manifest (pip install pyyaml)"
    try:
        data = yaml.safe_load(mpath.read_text(encoding="utf-8")) or {}
    except Exception as e:
        return False, None, f"manifest yaml error: {e}"

    # minimal schema
    required = ("name", "author", "description", "version")
    missing = [k for k in required if not data.get(k)]
    if missing:
        return False, data, f"manifest missing fields: {', '.join(missing)}"

    # entry_point, if present, must match this file
    ep = data.get("entry_point")
    if ep and Path(ep).resolve() != py_path.resolve():
        return False, data, f"manifest entry_point mismatch (got {ep})"

    # optional type checks
    if "tags" in data and not isinstance(data["tags"], (list, tuple)):
        return False, data, "manifest `tags` must be a list"
    return True, data, None

def _time_update_loop(mod: ModuleType, ctx, frames: int, dt: float, threshold_ms: float = 5.0):
    """
    Measure per-frame update() wall time.
    Returns dict: {avg_ms, min_ms, max_ms, over_threshold, threshold_ms}
    """
    times = []
    over = 0
    if not hasattr(mod, "update") or not callable(mod.update):
        return {"avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "over_threshold": 0, "threshold_ms": threshold_ms}
    for i in range(frames):
        ctx._frame = i
        t0 = time.perf_counter()
        mod.update(ctx, dt)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        times.append(dt_ms)
        if dt_ms > threshold_ms:
            over += 1
    if not times:
        return {"avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "over_threshold": 0, "threshold_ms": threshold_ms}
    return {
        "avg_ms": sum(times)/len(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "over_threshold": over,
        "threshold_ms": threshold_ms,
    }

class _DummyCtx:
    def __init__(self):
        self._frame = 0
        self.phase = 0.0
        self._logs = []
    def set_param(self, region, key, value): pass
    def pulse(self, region, duration=12): pass
    def jitter(self, x, y): pass
    def add_osc_filter_scope_default(self, name_prefix="demo", x=80, y=80): pass
    def frame(self): return self._frame
    def log(self, msg): self._logs.append(msg)
    def query_state(self, region=None): return {}
    def add_connection(self, src_region, src_channel, dst_region, dst_channel, cyclic=False): return True
    def remove_region(self, name): return True
    def get_logs(self): return self._logs

def _import_module_from_path(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return mod

def validate_program(path: str | Path, frames=100, dt=1/60.0, report_path=None, silent=False, strict_doc=False, verbose=False, perf_threshold_ms: float = 5.0) -> dict:
    path = Path(path)
    result = {
        "path": str(path),
        "exists": path.exists(),
        "import_ok": False,
        "has_setup": False,
        "has_update": False,
        "has_on_event": False,
        "setup_ok": False,
        "update_ok": False,
        "event_ok": False,
        "manifest_ok": False,
        "manifest": {},
        "signature_ok": True, # Assume true, set to false on failure
        "docstrings_ok": False,
        "exceptions": [],
        "warnings": [],
        "frames_run": 0,
        "dt": dt,
        "logs": [],
        "performance": None
    }

    if not path.exists():
        result["exceptions"].append(f"File not found: {path}")
        return result

    # Manifest validation
    m_ok, m_data, m_err = _validate_manifest_for(path)
    result["manifest_ok"] = m_ok
    result["manifest"] = m_data or {}
    if not m_ok:
        result["exceptions"].append(m_err)

    # Static check via AST
    meta = _ast_metadata(path)
    if meta.get("error"):
        result["exceptions"].append(meta["error"])
        return result
    result["has_setup"] = meta["has_setup"]
    result["has_update"] = meta["has_update"]
    result["has_on_event"] = meta["has_on_event"]

    # Check docstrings
    docstring_errors = []
    if meta["has_setup"]:
        setup_node = meta["func_nodes"].get("setup")
        if setup_node and not ast.get_docstring(setup_node):
             docstring_errors.append("missing_docstring_setup")
    if meta["has_update"]:
        update_node = meta["func_nodes"].get("update")
        if update_node and not ast.get_docstring(update_node):
            docstring_errors.append("missing_docstring_update")
    if meta["has_on_event"]:
        on_event_node = meta["func_nodes"].get("on_event")
        if on_event_node and not ast.get_docstring(on_event_node):
            docstring_errors.append("missing_docstring_on_event")
    if strict_doc:
        result["exceptions"].extend(docstring_errors)
    else:
        result["warnings"].extend(docstring_errors)
    result["docstrings_ok"] = len(docstring_errors) == 0

    # Dynamic check
    try:
        mod = _import_module_from_path(path)
        result["import_ok"] = True
    except Exception as e:
        result["exceptions"].append(f"import_error: {e}")
        return result

    # Signature checks
    ok, err = _check_hook_signature(mod, "setup", required=True)
    if not ok and err: result["exceptions"].append(err)
    ok, err = _check_hook_signature(mod, "update", required=True)
    if not ok and err: result["exceptions"].append(err)
    ok, err = _check_hook_signature(mod, "on_event", required=False)
    if not ok and err: result["exceptions"].append(err)
    result["signature_ok"] = not any("signature" in str(e) or "missing " in str(e) for e in result["exceptions"])

    ctx = _DummyCtx()

    if hasattr(mod, "setup") and callable(mod.setup):
        try:
            mod.setup(ctx)
            result["setup_ok"] = True
        except Exception as e:
            result["exceptions"].append(f"setup_error: {e}")

    # update() loop
    if hasattr(mod, "update") and callable(mod.update):
        try:
            perf = _time_update_loop(mod, ctx, frames, dt, perf_threshold_ms)
            result["frames_run"] = frames
            result["update_ok"] = True
            result["performance"] = perf
        except Exception as e:
            result["exceptions"].append(f"update_error_at_frame_{result.get('frames_run', 0)}: {e}")
            result["performance"] = {"error": str(e)}

    # on_event() smoke test
    if hasattr(mod, "on_event") and callable(mod.on_event):
        try:
            mod.on_event(ctx, {"type": "click", "x": 100, "y": 100})
            result["event_ok"] = True
        except Exception as e:
            result["warnings"].append(f"event_error: {e}")

    result["valid"] = len(result["exceptions"]) == 0
    return result

def print_validation_report(result, frames, ok):
    status = "✅ PASS" if ok else "❌ FAIL"
    hooks = "".join(["S" if result["has_setup"] else "-",
                     "U" if result["has_update"] else "-",
                     "E" if result["has_on_event"] else "-"])

    perf_summary = ""
    if result.get('performance'):
        perf = result['performance']
        perf_summary = (f"Perf: avg={perf['avg_ms']:.2f}ms max={perf['max_ms']:.2f}ms (threshold={perf['threshold_ms']:.2f}ms, over={perf['over_threshold']}/{frames})")

    print(f"{status} {result['path']} hooks={hooks} frames={result['frames_run']}")
    if perf_summary:
        print(perf_summary)
    if result["exceptions"]:
        print("Errors:")
        for ex in result["exceptions"]:
            print(f"  - {ex}")
    if result["warnings"]:
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"  - {warning}")
    if result["logs"]:
        print("Logs:")
        for log in result["logs"]:
            print(f"  - {log}")


def _maybe_write_report(report_path, result, ok):
    if not report_path:
        return
    rp = Path(report_path)
    rp.parent.mkdir(parents=True, exist_ok=True)

    # Create a copy to modify for the report
    report_data = result.copy()
    if "manifest" in report_data and report_data.get("manifest"):
        report_data["manifest"] = list(report_data["manifest"].keys())

    # Write JSON
    rp.with_suffix(".json").write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    # Write Markdown
    md = [
        f"# Validation Report for {result['path']}",
        f"- Status: {'PASS' if ok else 'FAIL'}",
        f"- Manifest OK: {result.get('manifest_ok')}",
    ]
    if result.get('manifest'):
        md.append(f"- Manifest Keys: {', '.join(result.get('manifest', {}).keys())}")

    if result.get("performance"):
        perf = result["performance"]
        md.append(f"- Perf: avg={perf.get('avg_ms', 0):.1f}ms max={perf.get('max_ms', 0):.1f}ms (threshold={perf.get('threshold_ms', 0):.1f}ms, over={perf.get('over_threshold', 0)}/{result.get('frames_run', 0)})")

    md.append(f"- Signature OK: {result.get('signature_ok')}")

    if result.get("exceptions"):
        md.append(f"- Exceptions:")
        md.extend([f"  - {e}" for e in result["exceptions"]])

    if result.get("warnings"):
        md.append(f"- Warnings:")
        md.extend([f"  - {w}" for w in result["warnings"]])

    rp.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")

# === CLI Handlers ===
def scaffold_program(path: str, force: bool = False, is_plugin: bool = False):
    """Generate a PXOS program or plugin template and manifest at the given path."""
    path = Path(path)
    if path.exists() and not force:
        confirm = input(f"⚠️ {path} exists. Overwrite? [y/N] ").lower().strip()
        if confirm != "y":
            raise FileExistsError(f"{path} exists. Use --force to overwrite without prompt.")
    os.makedirs(path.parent, exist_ok=True)
    base = path.stem
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", base)
    template = PLUGIN_TEMPLATE if is_plugin else PROGRAM_TEMPLATE
    contents = template.format(name=base, slug=slug)
    path.write_text(contents, encoding="utf-8")
    manifest_path = path.parent / f"{base}_manifest.yaml"
    manifest_content = MANIFEST_TEMPLATE.format(name=base)
    manifest_path.write_text(manifest_content, encoding="utf-8")
    print(f"🆕 Created {'plugin' if is_plugin else 'program'} at {path}")
    print(f"🗂️ Created manifest at {manifest_path}")
    print(f"Run: python program_host.py --show --program {path}")

def submit_program(
    program_path: str | Path,
    force: bool = False,
    frames: int = 100,
    perf_threshold_ms: float = 5.0,
    strict_perf: bool = False,
    require_manifest: bool = True,
) -> bool:
    p = Path(program_path)
    if not p.exists():
        print(f"❌ File not found: {p}")
        return False

    validation_result = validate_program(
        p, frames=frames, perf_threshold_ms=perf_threshold_ms
    )

    ok = validation_result["valid"]
    if require_manifest and not validation_result.get("manifest_ok", False):
        ok = False

    perf = validation_result.get("performance")
    if strict_perf and perf and perf["max_ms"] > perf["threshold_ms"]:
        ok = False

    if not ok:
        print("❌ Validation failed:")
        for e in validation_result["errors"]:
            print(f"  - {e}")
        return False
    for w in validation_result["warnings"]:
        print(f"⚠️ {w}")

    dest_dir = Path("programs")
    dest_dir.mkdir(exist_ok=True)
    dest_prog = dest_dir / p.name
    if dest_prog.exists() and not force:
        print(f"❌ Destination exists: {dest_prog} (use --force to overwrite)")
        return False

    shutil.copy2(p, dest_prog)
    manifest_path = p.with_name(f"{p.stem}_manifest.yaml")
    if manifest_path.exists():
        shutil.copy2(manifest_path, dest_dir / manifest_path.name)

    prog_checksum = _sha256(str(dest_prog))
    man_checksum = _sha256(str(dest_dir / manifest_path.name)) if manifest_path.exists() else None

    enriched_entry = {
        "name": validation_result["manifest"].get("name", p.stem),
        "version": validation_result["manifest"].get("version", "1.0.0"),
        "author": validation_result["manifest"].get("author", "Unknown"),
        "description": validation_result["manifest"].get("description", ""),
        "tags": validation_result["manifest"].get("tags", []),
        "path": str(dest_prog),
        "manifest": str(dest_dir / manifest_path.name) if manifest_path.exists() else None,
        "checksum": {"program_sha256": prog_checksum, "manifest_sha256": man_checksum},
        "last_modified": datetime.now().isoformat(),
        "perf": {
            "avg_ms": round(validation_result["performance"].get("avg_ms", 0.0), 3),
            "max_ms": round(validation_result["performance"].get("max_ms", 0.0), 3),
            "slow_frames": validation_result["performance"].get("over_threshold", 0),
            "threshold_ms": perf_threshold_ms
        },
        "perf_ok": validation_result["performance"].get("max_ms", 0.0) <= perf_threshold_ms if validation_result.get("performance") else True,
        "frames_validated": validation_result.get("frames_run", 0)
    }

    update_program_index(enriched_entry)

    print(f"✅ Submitted to {dest_prog}")
    return True

# === Context and RegionManager ===
class Region:
    def __init__(self, name, rect, params, channels, priority):
        self.name = name
        self.rect = rect
        self.params = params
        self.channels = channels
        self.priority = priority
        self.default_params = params.copy()

class RegionManager:
    def __init__(self):
        self.regions = []
        self.connections = []
        self.grid = type("Grid", (), {"occupied": {}, "regions": {}})()
    def connect(self, src_region, src_channel, dst_region, dst_channel, cyclic=False):
        self.connections.append(type("Connection", (), {
            "src_region": src_region, "src_channel": src_channel,
            "dst_region": dst_region, "dst_channel": dst_channel, "cyclic": cyclic
        })())
    def _mark_dirty(self, x, y, w, h): pass
    def add_region(self, name, rect=(0, 0, 1, 1), params=None, channels=None, priority=0):
        self.regions.append(Region(name, rect, params or {}, channels or [], priority))

class Context:
    def __init__(self, rm):
        self.rm = rm
        self.phase = 0.0
        self.frame_count = 0
        self.last_tap_region = None
        self.last_tap_time = 0
        self.DOUBLE_TAP_THRESHOLD = 0.3  # seconds

    def log(self, msg): print(f"[LOG] {msg}")
    def set_param(self, region, key, value): pass
    def pulse(self, region, duration=12): pass
    def jitter(self, x, y): pass
    def add_osc_filter_scope_default(self, name_prefix, x, y):
        self.rm.add_region(f"{name_prefix}_osc", (x, y, 1, 1), {"freq": 1.0, "amp": 1.0}, ["out"], 0)
        self.rm.add_region(f"{name_prefix}_filter", (x+1, y, 1, 1), {"cutoff": 1.0}, ["in", "out"], 1)
        self.rm.add_region(f"{name_prefix}_scope", (x+2, y, 1, 1), {}, ["in"], 2)
        self.add_connection(f"{name_prefix}_osc", "out", f"{name_prefix}_filter", "in")
        self.add_connection(f"{name_prefix}_filter", "out", f"{name_prefix}_scope", "in")
    def frame(self): return self.frame_count

    def query_state(self, region=None):
        rm = self.rm
        if region:
            r = next((x for x in rm.regions if x.name == region), None)
            return None if not r else {
                "name": r.name, "rect": r.rect, "params": dict(r.params),
                "channels": r.channels, "priority": r.priority
            }
        return {
            "regions": [
                {"name": r.name, "rect": r.rect, "params": dict(r.params),
                 "channels": r.channels, "priority": r.priority}
                for r in rm.regions
            ],
            "connections": [
                {"src": c.src_region, "src_ch": c.src_channel,
                 "dst": c.dst_region, "dst_ch": c.dst_channel, "cyclic": c.cyclic}
                for c in rm.connections
            ]
        }

    def add_connection(self, src_region, src_channel, dst_region, dst_channel, cyclic=False):
        try:
            self.rm.connect(src_region, src_channel, dst_region, dst_channel, cyclic=cyclic)
            self.log(f"➕ connect {src_region}.{src_channel} → {dst_region}.{dst_channel}"
                     + (" (cyclic)" if cyclic else ""))
            return True
        except Exception as e:
            self.log(f"❌ connect failed: {e}")
            return False

    def remove_region(self, name: str):
        rm = self.rm
        idx = next((i for i, r in enumerate(rm.regions) if r.name == name), None)
        if idx is None:
            self.log(f"❌ no such region: {name}")
            return False
        r = rm.regions.pop(idx)
        gr, gc, gh, gw = rm.grid.regions.get(name, (None, None, None, None))
        if gr is not None:
            rm.grid.occupied[gr:gr+gh, gc:gc+gw] = False
            rm.grid.regions.pop(name, None)
        rm.connections = [c for c in rm.connections if c.src_region != name and c.dst_region != name]
        self.rm._mark_dirty(*r.rect)
        self.log(f"🗑️ removed region {name}")
        return True

    def on_touch_down(self, x, y, region=None):
        current_time = time.time()
        if (self.last_tap_region == region and
            current_time - self.last_tap_time < self.DOUBLE_TAP_THRESHOLD):
            self.reset_region_defaults(region)
            self.last_tap_region = None
        else:
            self.last_tap_region = region
            self.last_tap_time = current_time

    def reset_region_defaults(self, region):
        if hasattr(region, 'default_params'):
            for param, value in region.default_params.items():
                self.set_param(region.name, param, value)
            self.log(f"🔄 Reset {region.name} to defaults")

    def duplicate_region(self, original_region):
        base_name = original_region.name
        if "_copy" in base_name:
            base_name = base_name.split("_copy")[0]
        existing_regions = [r.name for r in self.rm.regions]
        copy_numbers = []
        for name in existing_regions:
            if name.startswith(base_name):
                suffix = name[len(base_name):]
                if suffix.startswith("_"):
                    try:
                        num = int(suffix[1:])
                        copy_numbers.append(num)
                    except ValueError:
                        pass
        next_num = max(copy_numbers) + 1 if copy_numbers else 2
        new_name = f"{base_name}_{next_num}"
        self.log(f"🔄 Duplicated {original_region.name} as {new_name}")
        return new_name

# === CLI Setup ===
def main():
    parser = argparse.ArgumentParser(description="PXOS Program Host")
    parser.add_argument("--create-program", help="Path for new program template (e.g., examples/my_program.py)")
    parser.add_argument("--create-plugin", help="Path for new plugin template (e.g., plugins/wave_interference.py)")
    parser.add_argument("--list-programs", action="store_true", help="List all valid programs")
    parser.add_argument("--validate-program", help="Validate a program file")
    parser.add_argument("--validate-frames", type=int, default=100, help="Frames to run during validation")
    parser.add_argument("--validation-report", help="Write validation report to this path")
    parser.add_argument("--submit-program", help="Submit a program to programs/")
    parser.add_argument("--force", action="store_true", help="Overwrite files without prompt")
    parser.add_argument("--strict-doc", action="store_true", help="Fail validation if hooks lack docstrings")
    parser.add_argument("--require-manifest", action="store_true",
                        help="Fail validation if sidecar manifest is missing/invalid")
    parser.add_argument("--perf-threshold-ms", type=float, default=5.0,
                        help="Warn/fail if update() exceeds this per-frame time (ms)")
    parser.add_argument("--strict-perf", action="store_true",
                        help="Non-zero exit if max update() > threshold")
    parser.add_argument("--verbose", action="store_true", help="Print detailed error traces")
    parser.add_argument("--show", action="store_true", help="Show simulator output")
    parser.add_argument("--program", help="Path to program file to run")
    args = parser.parse_args()

    # === Handle CLI Commands ===
    if args.create_program:
        try:
            scaffold_program(args.create_program, args.force, is_plugin=False)
            sys.exit(0)
        except Exception as e:
            print(f"❌ Scaffold failed: {str(e)}")
            if args.verbose:
                traceback.print_exc()
            sys.exit(1)

    if args.create_plugin:
        try:
            scaffold_program(args.create_plugin, args.force, is_plugin=True)
            sys.exit(0)
        except Exception as e:
            print(f"❌ Plugin scaffold failed: {str(e)}")
            if args.verbose:
                traceback.print_exc()
            sys.exit(1)

    if args.list_programs:
        list_programs()
        sys.exit(0)

    if args.validate_program:
        result = validate_program(
            args.validate_program,
            frames=args.validate_frames,
            report_path=args.validation_report,
            strict_doc=args.strict_doc,
            verbose=args.verbose,
            perf_threshold_ms=args.perf_threshold_ms
        )

        ok = len(result["exceptions"]) == 0

        if args.require_manifest and not result.get("manifest_ok", False):
            ok = False

        perf = result.get("performance")
        if args.strict_perf and perf and perf["max_ms"] > perf["threshold_ms"]:
            ok = False

        print_validation_report(result, args.validate_frames, ok)
        _maybe_write_report(args.validation_report, result, ok)

        sys.exit(0 if ok else 2)

    if args.submit_program:
        submit_program(
            args.submit_program,
            force=args.force,
            frames=args.validate_frames,
            perf_threshold_ms=args.perf_threshold_ms,
            strict_perf=args.strict_perf,
            require_manifest=args.require_manifest,
        )
        sys.exit(0)

    # === Simulator Run ===
    if args.program:
        print(f"🚀 Running program: {args.program}")
        ctx = Context(RegionManager())
        spec = importlib.util.spec_from_file_location("program", args.program)
        if not spec or not spec.loader:
            print(f"❌ Failed to load program: {args.program}")
            sys.exit(1)
        module = importlib.util.module_from_spec(spec)
        sys.modules[Path(args.program).stem] = module
        spec.loader.exec_module(module)

        # Simulate 100 frames
        if hasattr(module, 'setup'):
            module.setup(ctx)
        if hasattr(module, 'update'):
            for _ in range(100):
                ctx.frame_count += 1
                module.update(ctx, 0.016)
        if hasattr(module, 'on_event'):
            ctx.on_touch_down(100, 100, Region("demo_osc", (80, 80, 1, 1), {"freq": 1.0}, ["out"], 0))
        print("✅ Simulated run complete")

if __name__ == "__main__":
    main()
