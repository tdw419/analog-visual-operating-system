#!/usr/bin/env python3
"""
LM Studio Automation Script v3.5
-------------------------------------------------------------------
Automates PXOS development with a self-correcting agent loop:
- Structured YAML task parsing from tasks.md
- Task status logging in task_log.json
- Multi-agent architecture: Planning, Code Generation, Critic/Verifier, Remediation
- Diff-based patching with validation and rollback
- RRE (Recursive Reflection Engine) for iterative improvement
- PXRaid for distributed task processing
- zTXt persistence and PXDigest for state saving
- Flask API with WebSocket for HTML UI integration
- Integration with program_host.py for atomic index updates
"""
import requests
from pxos_py.trust.network import NetworkGuard
import subprocess
import time
import json
import os
import ast
import re
import git
import yaml
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from glob import glob
import diff_match_patch as dmp_module
from PIL import Image
from io import BytesIO
from flask import Flask, request, jsonify
from flask_sock import Sock
from multiprocessing import Pool
from jsonschema import validate, ValidationError
from filelock import FileLock, Timeout
from program_host import validate_program, scaffold_program, update_program_index, INDEX_PATH, INDEX_LOCK, INDEX_TIMEOUT_SEC

# === CONFIG ===
LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen2.5-coder:7b"
TASKS_FILE = "tasks.md"
TASK_LOG = "task_log.json"
PROJECT_FILES = ["screen_native_sim.py", "program_host.py", "visual_isa.py", "programs/*.py", "examples/*.py", "plugins/*.py"]
GIT_COMMIT = True
TEST_COMMAND = ["python", "screen_native_sim.py", "--steps", "50", "--headless"]
TASK_GENERATION_INTERVAL = 3600
SNAPSHOT_DIR = "snapshots"
MAX_REFLECTION_DEPTH = 5
CONVERGENCE_THRESHOLD = 0.9
SYSTEM_PROMPT = """
You are an AI pair programmer for PXOS. Return ONLY valid Python code or unified diff patches.
No markdown, no code fences, no prose.
Preserve all existing behavior unless the task says otherwise.
If unsure, keep the original code and make minimal, surgical edits.
"""
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

# === JSON Schema for LM Studio Responses ===
PATCH_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["file", "patch"],
        "properties": {
            "file": {"type": "string"},
            "patch": {"type": "string"}
        }
    }
}

# === Task Management ===
def load_tasks():
    """Load structured tasks from tasks.md (YAML format)"""
    try:
        tasks = yaml.safe_load(Path(TASKS_FILE).read_text(encoding="utf-8")) or []
        pending = [t for t in tasks if t.get("status") == "pending"]
        completed_tasks = set(load_task_log().keys())
        valid_tasks = []
        for task in pending:
            deps = task.get("dependencies", [])
            if all(dep in completed_tasks for dep in deps):
                valid_tasks.append(task)
            else:
                print(f"⚠️ Skipping task {task['id']}: unresolved dependencies {deps}")
        return sorted(valid_tasks, key=lambda t: t.get("priority", 1))
    except Exception as e:
        print(f"❌ Failed to load tasks: {e}")
        return []

def log_task_status(task_id, status, notes=None):
    """Log task status to task_log.json"""
    log_path = Path(TASK_LOG)
    log = {}
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            print(f"⚠️ Corrupted task_log.json, starting fresh")
    log[task_id] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "notes": notes or ""
    }
    with FileLock(str(log_path) + ".lock"):
        log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"📜 Logged task {task_id}: {status}")

def load_task_log():
    """Load task_log.json"""
    log_path = Path(TASK_LOG)
    if log_path.exists():
        try:
            return json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            print(f"⚠️ Corrupted task_log.json, returning empty log")
            return {}
    return {}

def mark_task_completed(task_id):
    """Mark a task as completed in tasks.md"""
    tasks = yaml.safe_load(Path(TASKS_FILE).read_text(encoding="utf-8")) or []
    for task in tasks:
        if task.get("id") == task_id:
            task["status"] = "completed"
            break
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(tasks, f, indent=2)
    print(f"✅ Marked task {task_id} as completed in {TASKS_FILE}")

# === Flask App with WebSocket ===
app = Flask(__name__)
sock = Sock(app)

# === Atomic Index Helpers ===
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return None

def _sha256_of_text(txt: str) -> str:
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16]

def _read_json_safe(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        bad = path.with_suffix(f".corrupted.json.{int(time.time())}")
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

# === Code Manifest Generation ===
def generate_code_manifest():
    """Generate a YAML manifest of the codebase"""
    manifest = {
        "project": {
            "name": "PXOS",
            "version": "1.0.0",
            "description": "Pixel Operating System for visual programming",
            "author": "PXOS Team"
        },
        "files": []
    }
    for file in get_project_files():
        try:
            tree = ast.parse(Path(file).read_text(encoding="utf-8"), filename=file)
            functions = []
            classes = []
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    doc = ast.get_docstring(node) or ""
                    sig = f"def {node.name}({', '.join(arg.arg for arg in node.args.args)})"
                    functions.append({"name": node.name, "signature": sig, "docstring": doc})
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for method in node.body:
                        if isinstance(method, ast.FunctionDef):
                            doc = ast.get_docstring(method) or ""
                            sig = f"def {method.name}({', '.join(arg.arg for arg in method.args.args)})"
                            methods.append({"name": method.name, "signature": sig, "docstring": doc})
                    classes.append({"name": node.name, "docstring": ast.get_docstring(node) or "", "methods": methods})
            manifest["files"].append({
                "path": file,
                "functions": functions,
                "classes": classes
            })
        except Exception as e:
            print(f"⚠️ Failed to parse {file} for manifest: {e}")
    manifest_path = Path("code_manifest.yaml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, indent=2)
    return manifest

# === Expand Wildcards ===
def get_project_files():
    files = []
    for pattern in PROJECT_FILES:
        if "*" in pattern:
            files.extend([f for f in glob(pattern) if Path(f).is_file()])
        elif Path(pattern).is_file():
            files.append(pattern)
    return sorted(set(files))

# === LM Studio Helper ===
network_guard = NetworkGuard("net-policy.yaml")

def query_lmstudio(system_prompt, user_prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 4096
    }
    try:
        resp = network_guard.post(LMSTUDIO_API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
            validate(instance=data, schema=PATCH_SCHEMA)
            return content
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"❌ Invalid LM Studio response format: {e}")
            return None
    except requests.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

# === Validation and Cleaning ===
def is_valid_python(code):
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"

def strip_non_code(content):
    lines = content.splitlines()
    code_lines = []
    in_code_block = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not (line.strip().startswith("#") or line.strip() == ""):
            code_lines.append(line)
    return "\n".join(code_lines).strip()

# === Diff-Based Editing ===
def apply_diff_patch(target_file, original_content, patch_content):
    try:
        dmp = dmp_module.diff_match_patch()
        patches = dmp.patch_fromText(patch_content)
        patched_content, results = dmp.patch_apply(patches, original_content)
        if all(results):
            return patched_content, None
        else:
            return None, "Failed to apply some patches"
    except Exception as e:
        return None, f"Patch error: {e}"

# === zTXt Persistence ===
def save_snapshot(code_files, metrics, tasks):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snapshot_data = {
        "code_files": code_files,
        "metrics": metrics,
        "tasks": tasks,
        "timestamp": datetime.now().isoformat()
    }
    img = Image.new("RGB", (1, 1))
    img.info["zTXt"] = json.dumps(snapshot_data)
    snapshot_path = Path(SNAPSHOT_DIR) / f"snapshot_{int(time.time())}.png"
    start_time = time.perf_counter()
    img.save(snapshot_path, optimize=True)
    save_time = time.perf_counter() - start_time
    print(f"📸 Saved snapshot to {snapshot_path} (save time: {save_time:.3f}s)")
    return str(snapshot_path)

def load_from_pxdigest(snapshot_path):
    try:
        img = Image.open(snapshot_path)
        snapshot_data = json.loads(img.info.get("zTXt", "{}"))
        return snapshot_data.get("code_files", {}), snapshot_data.get("metrics", {}), snapshot_data.get("tasks", [])
    except Exception as e:
        print(f"❌ Failed to load PXDigest: {e}")
        return {}, {}, []

# === PXRaid Distribution ===
def pxraid_distribute(task, files, max_workers=4):
    def validate_chunk(file_subset):
        results = []
        for file in file_subset:
            if file.startswith(("programs/", "examples/", "plugins/")):
                result = validate_program(file, silent=True, strict_doc=True)
                results.append({"file": file, "valid": result["valid"], "performance": result["performance"]})
        return results
    chunk_size = max(1, len(files) // max_workers)
    chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]
    with Pool(max_workers) as pool:
        chunk_results = pool.map(validate_chunk, chunks)
    aggregated_results = []
    for chunk in chunk_results:
        aggregated_results.extend(chunk)
    return aggregated_results

# === Recursive Reflection Engine (RRE) ===
def reflect(diff, validation_results, test_output, depth=0):
    if depth >= MAX_REFLECTION_DEPTH:
        return {"task": None, "converged": False}
    system_msg = (
        "You are the Recursive Reflection Engine (RRE) for PXOS. "
        "Analyze the provided diff, validation results, and test output. "
        "Return a JSON object with 'task' (suggested improvement or None if converged) "
        "and 'converged' (boolean, True if no further improvements needed)."
    )
    user_msg = (
        f"Diff:\n{diff}\n\n"
        f"Validation Results:\n{json.dumps(validation_results, indent=2)}\n\n"
        f"Test Output:\n{test_output}\n\n"
        "Suggest a specific, actionable improvement task or indicate convergence."
    )
    try:
        response = query_lmstudio(system_msg, user_msg)
        if not response:
            return {"task": None, "converged": False}
        suggestion = json.loads(response)
        if suggestion["converged"] or suggestion["task"] is None:
            return {"task": None, "converged": True}
        return suggestion
    except Exception as e:
        print(f"❌ RRE reflection failed: {e}")
        return {"task": None, "converged": False}

# === Self-Correcting Agent Loop ===
def plan_task(task):
    """Planning Agent: Decompose task into actionable sub-tasks"""
    system_msg = (
        "You are the Planning Agent for PXOS. Decompose the provided task into a sequence of actionable sub-tasks. "
        "Return a JSON array of sub-tasks, each with 'id' (T### format), 'title', 'description', 'file' (target file), 'priority' (1-5), and 'dependencies' (list of sub-task IDs)."
    )
    user_msg = (
        f"Task ID: {task['id']}\n"
        f"Title: {task['title']}\n"
        f"Description: {task['description']}\n"
        f"Tags: {', '.join(task.get('tags', []))}\n\n"
        "Decompose into actionable sub-tasks, targeting specific files in: " + ", ".join(PROJECT_FILES)
    )
    try:
        response = query_lmstudio(system_msg, user_msg)
        if not response:
            return [task]
        sub_tasks = json.loads(response)
        return sorted(sub_tasks, key=lambda t: t.get("priority", 1))
    except Exception as e:
        print(f"❌ Task planning failed: {e}")
        return [task]

def generate_code(sub_task, file_contents):
    """Code Generation Agent: Produce diff patch for a sub-task"""
    system_msg = SYSTEM_PROMPT + (
        f"\nTask ID: {sub_task['id']}\n"
        f"Title: {sub_task['title']}\n"
        f"Description: {sub_task['description']}\n"
        "Return a JSON object with a single 'patch' field containing a unified diff patch for the specified file."
    )
    user_msg = (
        f"Target file: {sub_task['file']}\n"
        f"Current content:\n{file_contents.get(sub_task['file'], '# New file\n')}\n\n"
        "Generate a unified diff patch to implement the task."
    )
    try:
        response = query_lmstudio(system_msg, user_msg)
        if not response:
            return None, "No response from LM Studio"
        data = json.loads(response)
        return data["patch"], None
    except Exception as e:
        return None, f"Code generation failed: {e}"

def verify_code(target_file, patched_content, sub_task):
    """Critic/Verifier Agent: Validate and test the patched code"""
    is_valid, error = is_valid_python(patched_content)
    if not is_valid:
        return False, {"error": error}
    Path(target_file).write_text(patched_content, encoding="utf-8")
    validation_result = validate_program(target_file, silent=True, strict_doc=True)
    if not validation_result["valid"]:
        return False, {"error": "Program validation failed", "details": validation_result}
    try:
        result = subprocess.run(TEST_COMMAND, check=True, timeout=120, capture_output=True, text=True)
        return True, {"stdout": result.stdout, "stderr": result.stderr}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return False, {"error": str(e), "stdout": e.stdout if hasattr(e, "stdout") else "", "stderr": e.stderr if hasattr(e, "stderr") else ""}

def remediate_code(target_file, original_content, patched_content, sub_task, verification_result, repo):
    """Remediation Agent: Apply or rollback changes"""
    if verification_result.get("error"):
        print(f"❌ Verification failed for {sub_task['id']}: {verification_result['error']}")
        Path(target_file).write_text(original_content, encoding="utf-8")
        return False, verification_result["error"]
    Path(target_file).write_text(patched_content, encoding="utf-8")
    repo.git.add(target_file)
    if sub_task["file"].startswith(("programs/", "examples/", "plugins/")):
        validation_result = validate_program(target_file, silent=True, strict_doc=True)
        program_entry = {
            "name": validation_result["manifest"].get("name", Path(target_file).stem),
            "path": str(target_file),
            "description": validation_result["manifest"].get("description", "No description"),
            "author": validation_result["manifest"].get("author", "Unknown"),
            "version": validation_result["manifest"].get("version", "1.0.0"),
            "last_modified": datetime.now().isoformat(),
            "tags": validation_result["manifest"].get("tags", sub_task.get("tags", [])),
            "checksum": _sha256(target_file),
            "manifest_checksum": _sha256(f"{target_file.replace('.py', '')}_manifest.yaml")
                if os.path.exists(f"{target_file.replace('.py', '')}_manifest.yaml") else None,
            "validated_at": datetime.now().isoformat(),
            "perf": validation_result["performance"],
            "perf_ok": validation_result["performance"].get("max_ms", 0) <= validation_result["performance"].get("threshold_ms", 5.0),
            "docs": validation_result["docstrings"],
            "signatures_ok": validation_result["signature_ok"]
        }
        update_program_index(program_entry)
    return True, None

# === Program Generation ===
def generate_program(task: dict, target_path: str, repo):
    base = os.path.splitext(os.path.basename(target_path))[0]
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", base)
    system_msg = SYSTEM_PROMPT + (
        f"\nTask ID: {task['id']}\n"
        f"Title: {task['title']}\n"
        f"Description: {task['description']}\n"
        "Return a JSON object with: "
        "'code': the full Python code, "
        "'manifest': a dict with name, description, author, version, tags, entry_point, type, dependencies."
    )
    user_msg = (
        f"Create a PXOS program at {target_path} with name '{base}'. "
        f"Use this structure:\n"
        f"{PROGRAM_TEMPLATE.format(name=base, slug=slug)}"
    )
    try:
        response = query_lmstudio(system_msg, user_msg)
        if not response:
            log_task_status(task["id"], "failed", "No response from LM Studio")
            return False
        data = json.loads(response)
        code = strip_non_code(data["code"])
        is_valid, error = is_valid_python(code)
        if not is_valid:
            log_task_status(task["id"], "failed", f"Invalid generated code: {error}")
            print(f"❌ Invalid generated code: {error}")
            return False
        Path(target_path).write_text(code, encoding="utf-8")
        print(f"✨ Generated program: {target_path}")
        manifest = data.get("manifest", {})
        manifest["name"] = manifest.get("name", base)
        manifest["author"] = manifest.get("author", "LM Studio")
        manifest["description"] = manifest.get("description", f"Generated {base} program")
        manifest["version"] = manifest.get("version", "0.1.0")
        manifest["tags"] = manifest.get("tags", task.get("tags", ["generated"]))
        manifest["entry_point"] = str(target_path)
        manifest["type"] = "program"
        manifest["dependencies"] = []
        manifest_path = Path(target_path).parent / f"{base}_manifest.yaml"
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(manifest, f, indent=2)
        print(f"📄 Generated manifest: {manifest_path}")
        validation_result = validate_program(target_path, silent=True, strict_doc=True)
        if not validation_result["valid"]:
            log_task_status(task["id"], "failed", f"Generated program invalid: {validation_result['exceptions']}")
            print(f"❌ Generated program invalid: {target_path}")
            repo.git.reset("--", target_path, manifest_path)
            return False
        program_entry = {
            "name": validation_result["manifest"].get("name", base),
            "path": str(target_path),
            "description": validation_result["manifest"].get("description", "Generated program"),
            "author": validation_result["manifest"].get("author", "LM Studio"),
            "version": validation_result["manifest"].get("version", "0.1.0"),
            "last_modified": datetime.now().isoformat(),
            "tags": validation_result["manifest"].get("tags", task.get("tags", ["generated"])),
            "checksum": _sha256(str(target_path)),
            "manifest_checksum": _sha256(str(manifest_path)),
            "validated_at": datetime.now().isoformat(),
            "perf": validation_result["performance"],
            "perf_ok": validation_result["performance"].get("max_ms", 0) <= validation_result["performance"].get("threshold_ms", 5.0),
            "docs": validation_result["docstrings"],
            "signatures_ok": validation_result["signature_ok"]
        }
        update_program_index(program_entry)
        repo.git.add(target_path, manifest_path)
        log_task_status(task["id"], "completed", "Program generated and validated successfully")
        mark_task_completed(task["id"])
        return True
    except Exception as e:
        log_task_status(task["id"], "failed", f"Program generation failed: {e}")
        print(f"❌ Failed to generate program: {e}")
        return False

# === Auto-Task Generation ===
def generate_tasks(repo):
    files = get_project_files()
    file_contents = {}
    todos = []
    manifest = generate_code_manifest()
    for file in files:
        content = Path(file).read_text(encoding="utf-8")
        file_contents[file] = content
        for line_no, line in enumerate(content.splitlines(), 1):
            if "# TODO" in line:
                todo = line[line.find("# TODO") + 7:].strip()
                todos.append({
                    "id": f"T{len(todos) + 1:03d}",
                    "title": todo,
                    "description": f"Address TODO in {file}:{line_no}",
                    "priority": 1,
                    "tags": ["todo"],
                    "status": "pending",
                    "dependencies": []
                })
    system_msg = (
        "You are a code reviewer for the PXOS screen-native simulator. "
        "Analyze the provided code and manifest to suggest up to 5 specific, actionable improvements for inefficiencies, "
        "missing error handling, or optimization opportunities. "
        "Return a JSON array of objects with 'id' (T### format), 'title' (description), 'description' (detailed explanation), "
        "'file' (target file), 'priority' (1-5, 1 highest), 'tags' (list of strings), 'status' (pending), and 'dependencies' (list of task IDs)."
    )
    user_msg = (
        "Code manifest:\n" + yaml.dump(manifest, indent=2) +
        "\nProject files:\n" +
        "\n".join(f"--- {file} ---\n{content}" for file, content in file_contents.items()) +
        "\nSuggest improvements with priorities."
    )
    try:
        response = query_lmstudio(system_msg, user_msg)
        if response:
            suggestions = json.loads(response)
            if isinstance(suggestions, list):
                todos.extend(suggestions)
    except (json.JSONDecodeError, requests.RequestException) as e:
        print(f"⚠️ Failed to generate tasks: {e}")
    existing_tasks = load_tasks()
    existing_ids = {t["id"] for t in existing_tasks}
    new_tasks = [t for t in todos if t["id"] not in existing_ids]
    if new_tasks:
        print(f"📜 Generated {len(new_tasks)} new tasks")
        existing_tasks.extend(new_tasks)
        existing_tasks.sort(key=lambda t: t.get("priority", 1))
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(existing_tasks, f, indent=2)
        print(f"✨ Added {len(new_tasks)} new tasks to {TASKS_FILE}")
        repo.git.add(TASKS_FILE)

# === Auto-Dev Integration ===
def evolve_code(base_code_files, task, depth=0):
    repo = git.Repo(".")
    file_contents = {file: Path(file).read_text(encoding="utf-8") if Path(file).exists() else "# New file\n"
                     for file in base_code_files}
    manifest = generate_code_manifest()
    sub_tasks = plan_task(task)
    validation_results = []
    backups = {}
    for sub_task in sub_tasks:
        log_task_status(sub_task["id"], "processing", f"Started sub-task: {sub_task['title']}")
        patch, error = generate_code(sub_task, file_contents)
        if error:
            log_task_status(sub_task["id"], "failed", error)
            continue
        target_file = sub_task["file"]
        original_content = file_contents.get(target_file, "# New file\n")
        patched_content, patch_error = apply_diff_patch(target_file, original_content, patch)
        if patch_error:
            log_task_status(sub_task["id"], "failed", patch_error)
            validation_results.append({"file": target_file, "error": patch_error})
            continue
        backup_file = f"{target_file}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(target_file):
            Path(backup_file).write_text(original_content, encoding="utf-8")
            backups[target_file] = backup_file
        success, verification_result = verify_code(target_file, patched_content, sub_task)
        if not success:
            log_task_status(sub_task["id"], "failed", verification_result["error"])
            validation_results.append({"file": target_file, "error": verification_result["error"], "details": verification_result})
            continue
        success, remediation_error = remediate_code(target_file, original_content, patched_content, sub_task, verification_result, repo)
        if not success:
            log_task_status(sub_task["id"], "failed", remediation_error)
            validation_results.append({"file": target_file, "error": remediation_error})
            continue
        validation_results.append({"file": target_file, "success": True, "performance": verification_result.get("performance", {})})
        file_contents[target_file] = patched_content
    if not all(v.get("success", False) for v in validation_results):
        print("❌ One or more sub-tasks failed. Rolling back all changes.")
        for file, backup_file in backups.items():
            Path(file).write_text(Path(backup_file).read_text(encoding="utf-8"), encoding="utf-8")
            print(f"🔄 Restored {file} from {backup_file}")
        log_task_status(task["id"], "failed", "Sub-task failures")
        return {"success": False, "error": "Sub-task failures", "validation_results": validation_results}
    try:
        result = subprocess.run(TEST_COMMAND, check=True, timeout=120, capture_output=True, text=True)
        test_output = result.stdout + result.stderr
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        test_output = str(e)
        print(f"❌ Tests failed: {e}. Restoring backups.")
        for file, backup_file in backups.items():
            Path(file).write_text(Path(backup_file).read_text(encoding="utf-8"), encoding="utf-8")
            print(f"🔄 Restored {file} from {backup_file}")
            repo.git.add(file)
            repo.index.commit(f"Revert: {task['title']} ({datetime.now().isoformat()})")
        log_task_status(task["id"], "failed", f"Tests failed: {e}")
        return {"success": False, "error": str(e), "validation_results": validation_results}
    reflection = reflect("\n".join(v.get("patch", "") for v in validation_results if v.get("patch")), validation_results, test_output, depth)
    if not reflection["converged"] and reflection["task"]:
        print(f"🧠 RRE suggests improvement: {reflection['task']}")
        new_task = {
            "id": f"T{int(task['id'][1:]) + 1:03d}",
            "title": reflection["task"],
            "description": f"Refinement for {task['title']}",
            "priority": task.get("priority", 1),
            "tags": task.get("tags", []) + ["refinement"],
            "status": "pending",
            "dependencies": [task["id"]]
        }
        tasks = yaml.safe_load(Path(TASKS_FILE).read_text(encoding="utf-8")) or []
        tasks.append(new_task)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(tasks, f, indent=2)
        repo.git.add(TASKS_FILE)
        log_task_status(task["id"], "refined", f"New task created: {new_task['id']}")
        return evolve_code(base_code_files, new_task, depth + 1)
    snapshot_path = save_snapshot(file_contents, validation_results, [task])
    if GIT_COMMIT:
        commit_msg = f"Auto: {task['title']} ({datetime.now().isoformat()})"
        repo.git.add(list(backups.keys()) + [TASKS_FILE])
        repo.index.commit(commit_msg)
        print(f"📦 Changes committed: {commit_msg}")
    log_task_status(task["id"], "completed", "Task successfully processed")
    mark_task_completed(task["id"])
    return {
        "success": True,
        "validation_results": validation_results,
        "snapshot_path": snapshot_path,
        "metrics": {
            "generations": depth + 1,
            "converged": reflection["converged"],
            "timestamp": datetime.now().isoformat()
        }
    }

# === Flask API Endpoints ===
@app.route("/api/start-auto-dev", methods=["POST"])
def start_auto_dev():
    data = request.json
    task = data.get("task")
    if not task or not task.get("id"):
        return jsonify({"success": False, "error": "Invalid or missing task ID"}), 400
    files = data.get("files", get_project_files())
    result = evolve_code(files, task)
    return jsonify(result)

@app.route("/api/run-rre", methods=["POST"])
def run_rre():
    data = request.json
    diff = data.get("diff", "")
    validation_results = data.get("validation_results", [])
    test_output = data.get("test_output", "")
    result = reflect(diff, validation_results, test_output)
    return jsonify(result)

@app.route("/api/run-pxraid", methods=["POST"])
def run_pxraid():
    data = request.json
    task = data.get("task", {"title": "Validate programs", "id": "T000"})
    files = data.get("files", get_project_files())
    result = pxraid_distribute(task, files)
    log_task_status(task["id"], "completed", f"PXRaid validation completed with {len(result)} results")
    return jsonify({"success": True, "results": result})

@app.route("/api/load-pxdigest", methods=["POST"])
def load_pxdigest():
    data = request.json
    snapshot_path = data.get("snapshot_path")
    code_files, metrics, tasks = load_from_pxdigest(snapshot_path)
    return jsonify({"code_files": code_files, "metrics": metrics, "tasks": tasks})

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    metrics = {}
    index_file = Path("programs/program_index.json")
    if index_file.exists():
        metrics["program_index"] = _read_json_safe(index_file)
    task_log = load_task_log()
    metrics["task_log"] = task_log
    manifest = generate_code_manifest()
    metrics["code_manifest"] = manifest
    return jsonify(metrics)

@app.route("/")
def serve_ui():
    try:
        with open("pxdevlab2123456789.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Control panel not found. Please create pxdevlab2123456789.html.", 404

@sock.route("/ws/logs")
def ws_logs(ws):
    while True:
        metrics = {}
        index_file = Path("programs/program_index.json")
        if index_file.exists():
            metrics["program_index"] = _read_json_safe(index_file)
        metrics["task_log"] = load_task_log()
        metrics["code_manifest"] = generate_code_manifest()
        ws.send(json.dumps(metrics))
        time.sleep(10)

# === Main Loop ===
def run_automation_loop(dry_run=False, verbose=False):
    repo = git.Repo(".")
    if not os.path.exists(TASKS_FILE):
        print(f"❌ {TASKS_FILE} not found. Creating default task queue.")
        default_tasks = [
            {
                "id": "T001",
                "title": "Add click-to-perturb in Visual ISA",
                "description": "Implement click-to-perturb in Visual ISA (no UI text output; just code)",
                "priority": 1,
                "tags": ["visual_isa", "interaction"],
                "status": "pending",
                "dependencies": []
            },
            {
                "id": "T002",
                "title": "Add TouchController.on_mouse_move param mapping",
                "description": "Add on_mouse_move handler to TouchController; map drag to tau/freq",
                "priority": 2,
                "tags": ["touch_controller", "interaction"],
                "status": "pending",
                "dependencies": []
            },
            {
                "id": "T003",
                "title": "Clamp params using PARAM_BOUNDS",
                "description": "Clamp parameters using PARAM_BOUNDS if present",
                "priority": 3,
                "tags": ["parameters", "validation"],
                "status": "pending",
                "dependencies": []
            }
        ]
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(default_tasks, f, indent=2)
        repo.git.add(TASKS_FILE)

    last_task_generation = 0
    while True:
        if time.time() - last_task_generation > TASK_GENERATION_INTERVAL and not dry_run:
            print("🧠 Scanning for new tasks...")
            generate_tasks(repo)
            last_task_generation = time.time()
        tasks = load_tasks()
        if not tasks:
            print("✅ No pending tasks in tasks.md — sleeping.")
            time.sleep(60)
            continue
        current_task = tasks[0]
        print(f"\n📌 Current task: {current_task['id']} - {current_task['title']}")
        log_task_status(current_task["id"], "processing", f"Started task: {current_task['title']}")
        if dry_run:
            print(f"📝 Dry run: Would process task {current_task['id']}")
            log_task_status(current_task["id"], "skipped", "Dry run mode")
            time.sleep(5)
            continue
        if current_task["title"].lower().startswith(("generate new program:", "create new program")):
            try:
                target_path = current_task.get("files_to_edit", [f"programs/{current_task['id'].lower()}.py"])[0]
                if generate_program(current_task, target_path, repo):
                    if GIT_COMMIT:
                        commit_msg = f"Auto: Generated program {Path(target_path).stem} ({datetime.now().isoformat()})"
                        repo.index.commit(commit_msg)
                        print(f"📦 Changes committed: {commit_msg}")
                time.sleep(10)
                continue
            except Exception as e:
                log_task_status(current_task["id"], "failed", f"Program generation failed: {e}")
                print(f"❌ Program generation failed: {e}")
                time.sleep(10)
                continue
        result = evolve_code(get_project_files(), current_task)
        if result["success"]:
            print(f"✅ Task {current_task['id']} completed successfully")
        else:
            print(f"❌ Task {current_task['id']} failed: {result.get('error', 'Unknown error')}")
        time.sleep(10)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PXOS Auto-Dev Loop")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode without applying changes")
    parser.add_argument("--verbose", action="store_true", help="Print detailed logs")
    parser.add_argument("--run-api", action="store_true", help="Run Flask API for UI integration")
    args = parser.parse_args()

    if args.run_api:
        print("🚀 Starting Flask API for PXOS UI")
        app.run(debug=False, host="0.0.0.0", port=5000)
    else:
        print(f"🚀 Starting LM Studio Automation (Dry-run: {args.dry_run}, Verbose: {args.verbose})")
        run_automation_loop(dry_run=args.dry_run, verbose=args.verbose)
