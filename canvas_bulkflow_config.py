import os


def load_env_file():
    """
    Load key=value pairs from canvas_bulkflow.env (if present) into os.environ.
    Lines starting with # are ignored.
    """
    env_path = os.path.join(os.path.dirname(__file__), "canvas_bulkflow.env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass
