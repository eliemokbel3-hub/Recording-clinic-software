"""Task P.0 - prose-runtime preflight (plan-note-learning-and-styles, Task 4.0 / D8).

Run this YOURSELF from a NORMAL terminal (PowerShell or cmd), never from an agent
shell - it fetches wheels and a tiny smoke model over the network:

    py -3.14 scripts\\preflight-prose-runtime.py
    py -3.14 scripts\\preflight-prose-runtime.py --python 3.12      (fallback: after `py install 3.12`)
    py -3.14 scripts\\preflight-prose-runtime.py --only llama       (one candidate only)

What it does, per candidate runtime:
  1. creates a THROWAWAY venv under %TEMP%\\prose-preflight\\ (nothing touches the project venv);
  2. resolves the package as a PREBUILT WHEEL ONLY (`--only-binary=:all:` - a source build is
     refused, which is D8's contract) and records the wheel URL, version and sha256 that pip
     itself reports (`pip install --report`);
  3. installs it and times the install;
  4. runs an import + a ten-token smoke generation and times it.

Candidates:
  llama  - llama-cpp-python from its documented prebuilt CPU wheel index; smoke = a ten-token
           chat completion on a ~100 MB GGUF (SmolLM2-135M-Instruct Q4_K_M from Hugging Face).
  genai  - onnxruntime-genai from PyPI; smoke = import + version (a ten-token generation needs a
           genai-exported ONNX model directory; pass --genai-model <dir> if you have one).

It prints ONE `=== P.0 RESULT ===` block at the end and writes the same JSON to
%TEMP%\\prose-preflight\\preflight-report.json. Paste the block back into the session.
No file in the repository is written or read by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LLAMA_CPU_INDEX = "https://abetlen.github.io/llama-cpp-python/whl/cpu"
SMOKE_REPO = "bartowski/SmolLM2-135M-Instruct-GGUF"
SMOKE_FILE = "SmolLM2-135M-Instruct-Q4_K_M.gguf"
SMOKE_PROMPT = "Rewrite as one clinical sentence: neck pain three days, worse turning left."

LLAMA_SMOKE = r"""
import json, time
import llama_cpp
from llama_cpp import Llama
t0 = time.time()
llm = Llama.from_pretrained(repo_id=%(repo)r, filename=%(file)r, n_ctx=512, verbose=False)
load_s = time.time() - t0
t0 = time.time()
out = llm.create_chat_completion(
    messages=[{"role": "user", "content": %(prompt)r}], max_tokens=10, temperature=0.0)
gen_s = time.time() - t0
print("SMOKE_JSON " + json.dumps({
    "runtime_version": llama_cpp.__version__,
    "model_load_seconds": round(load_s, 2),
    "ten_token_seconds": round(gen_s, 2),
    "completion_tokens": out["usage"]["completion_tokens"],
    "text": out["choices"][0]["message"]["content"],
}))
"""

GENAI_SMOKE = r"""
import json, time
import onnxruntime
import onnxruntime_genai as og
result = {"runtime_version": og.__version__, "onnxruntime_version": onnxruntime.__version__,
          "generation": "not run (no --genai-model directory given)"}
model_dir = %(model_dir)r
if model_dir:
    t0 = time.time()
    model = og.Model(model_dir)
    tok = og.Tokenizer(model)
    load_s = time.time() - t0
    params = og.GeneratorParams(model)
    params.set_search_options(max_length=64)
    gen = og.Generator(model, params)
    t0 = time.time()
    gen.append_tokens(tok.encode(%(prompt)r))
    n = 0
    while not gen.is_done() and n < 10:
        gen.generate_next_token()
        n += 1
    gen_s = time.time() - t0
    result.update({"model_load_seconds": round(load_s, 2), "ten_token_seconds": round(gen_s, 2),
                   "completion_tokens": n,
                   "text": tok.decode(gen.get_sequence(0)[-n:])})
print("SMOKE_JSON " + json.dumps(result))
"""


def sh(cmd: list[str], timeout: int = 1800) -> tuple[subprocess.CompletedProcess[str], float]:
    print("$ " + " ".join(cmd), flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    return proc, time.time() - t0


def make_venv(root: Path, pyver: str | None) -> Path:
    if root.exists():
        print(f"reusing throwaway venv {root}")
    else:
        launcher = ["py", f"-{pyver}"] if pyver else [sys.executable]
        proc, _ = sh([*launcher, "-m", "venv", str(root)])
        if proc.returncode:
            raise SystemExit(f"venv creation failed:\n{proc.stderr}")
    python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    proc, _ = sh([str(python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    if proc.returncode:
        raise SystemExit(f"pip upgrade failed:\n{proc.stderr}")
    return python


def resolve_wheel(python: Path, package: str, extra_index: str | None, report: Path) -> dict:
    """Ask pip which prebuilt wheel it WOULD install; refuse anything that is not a wheel."""
    cmd = [str(python), "-m", "pip", "install", "--dry-run", "--only-binary=:all:",
           "--report", str(report), package]
    if extra_index:
        cmd += ["--extra-index-url", extra_index]
    proc, seconds = sh(cmd)
    if proc.returncode:
        return {"status": "no-prebuilt-wheel", "pip_error": proc.stderr.strip()[-1500:],
                "resolve_seconds": round(seconds, 1)}
    data = json.loads(report.read_text(encoding="utf-8"))
    for item in data.get("install", []):
        if item["metadata"]["name"].lower().replace("_", "-") == package.lower():
            info = item["download_info"]
            return {"status": "wheel-found",
                    "version": item["metadata"]["version"],
                    "wheel_url": info["url"],
                    "sha256": info.get("archive_info", {}).get("hashes", {}).get("sha256"),
                    "resolve_seconds": round(seconds, 1)}
    return {"status": "resolve-error", "detail": "package missing from pip report"}


def install(python: Path, package: str, extra_index: str | None, extra_pkgs: list[str]) -> dict:
    cmd = [str(python), "-m", "pip", "install", "--only-binary=:all:", package, *extra_pkgs]
    if extra_index:
        cmd += ["--extra-index-url", extra_index]
    proc, seconds = sh(cmd)
    if proc.returncode:
        return {"status": "install-failed", "pip_error": proc.stderr.strip()[-1500:],
                "install_seconds": round(seconds, 1)}
    return {"status": "installed", "install_seconds": round(seconds, 1)}


def sha256_of_installed_wheel(python: Path, package: str) -> str | None:
    """Independent check: download the exact wheel pip chose and hash it ourselves."""
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [str(python), "-m", "pip", "download", "--only-binary=:all:", "--no-deps",
               "-d", tmp, package]
        if package.startswith("llama-cpp-python"):
            cmd += ["--extra-index-url", LLAMA_CPU_INDEX]
        proc, _ = sh(cmd)
        if proc.returncode:
            return None
        wheels = list(Path(tmp).glob("*.whl"))
        if len(wheels) != 1:
            return None
        return hashlib.sha256(wheels[0].read_bytes()).hexdigest()


def smoke(python: Path, code: str) -> dict:
    proc, seconds = sh([str(python), "-c", code], timeout=1800)
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("SMOKE_JSON ")), None)
    if proc.returncode or line is None:
        return {"status": "smoke-failed", "stderr": proc.stderr.strip()[-1500:],
                "stdout": proc.stdout.strip()[-500:], "wall_seconds": round(seconds, 1)}
    out = json.loads(line[len("SMOKE_JSON "):])
    out.update({"status": "smoke-ok", "wall_seconds": round(seconds, 1)})
    return out


def candidate(name: str, python: Path, args: argparse.Namespace, workdir: Path) -> dict:
    if name == "llama":
        package, index, extras = "llama-cpp-python", LLAMA_CPU_INDEX, ["huggingface_hub"]
        code = LLAMA_SMOKE % {"repo": SMOKE_REPO, "file": SMOKE_FILE, "prompt": SMOKE_PROMPT}
    else:
        package, index, extras = "onnxruntime-genai", None, []
        code = GENAI_SMOKE % {"model_dir": args.genai_model or "", "prompt": SMOKE_PROMPT}
    result: dict = {"package": package, "wheel_source": index or "https://pypi.org/simple"}
    result.update(resolve_wheel(python, package, index, workdir / f"{name}-report.json"))
    if result["status"] != "wheel-found":
        return result
    result.update(install(python, package, index, extras))
    if result["status"] != "installed":
        return result
    local_sha = sha256_of_installed_wheel(python, package)
    result["sha256_local_recheck"] = local_sha
    result["sha256_matches"] = (local_sha is not None and local_sha == result.get("sha256"))
    result.update(smoke(python, code))
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["llama", "genai"], help="run one candidate only")
    ap.add_argument("--python", dest="pyver", help="venv interpreter via the py launcher, e.g. 3.12")
    ap.add_argument("--genai-model", help="a genai-exported ONNX model directory for the genai smoke")
    ap.add_argument("--fresh", action="store_true", help="delete and recreate the throwaway venvs")
    args = ap.parse_args()

    workdir = Path(tempfile.gettempdir()) / "prose-preflight"
    workdir.mkdir(parents=True, exist_ok=True)
    report_path = workdir / "preflight-report.json"
    report: dict = {"task": "P.0 prose-runtime preflight", "host": platform.platform(),
                    "machine": platform.machine(), "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "candidates": {}}
    for name in ([args.only] if args.only else ["llama", "genai"]):
        print(f"\n===== candidate: {name} =====", flush=True)
        venv_root = workdir / f"venv-{name}-{args.pyver or 'default'}"
        if args.fresh and venv_root.exists():
            import shutil
            shutil.rmtree(venv_root)
        try:
            python = make_venv(venv_root, args.pyver)
            proc, _ = sh([str(python), "-c", "import sys; print(sys.version.split()[0])"])
            entry = {"python": proc.stdout.strip()}
            entry.update(candidate(name, python, args, workdir))
        except Exception as exc:  # noqa: BLE001 - a preflight reports, never crashes
            entry = {"status": "error", "detail": f"{type(exc).__name__}: {exc}"}
        report["candidates"][name] = entry
        print(json.dumps(entry, indent=2), flush=True)

    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n=== P.0 RESULT (paste this whole block back) ===")
    print(json.dumps(report, indent=2))
    print("=== END P.0 RESULT ===")
    print(f"\n(also saved to {report_path}; the throwaway venvs live under {workdir} and can be deleted)")


if __name__ == "__main__":
    main()
