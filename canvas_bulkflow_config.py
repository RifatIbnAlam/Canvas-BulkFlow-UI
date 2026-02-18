import os
import sys


def load_env_file(path="canvas_bulkflow.env"):
    candidate_paths = []

    # Explicit absolute path always wins.
    if os.path.isabs(path):
        candidate_paths.append(path)
    else:
        # For packaged EXE, load from EXE folder first.
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            candidate_paths.append(os.path.join(exe_dir, path))

        # Fallback to module folder and current working directory.
        module_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_paths.append(os.path.join(module_dir, path))
        candidate_paths.append(os.path.abspath(path))

    env_path = next((p for p in candidate_paths if os.path.exists(p)), None)
    if not env_path:
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        # If local env file cannot be read, continue with existing environment.
        pass
