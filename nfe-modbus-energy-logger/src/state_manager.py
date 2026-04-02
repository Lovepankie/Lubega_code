import json, os

def load(path):
    if not os.path.exists(path):
        return {}

    with open(path) as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)

def save(path, state):
    json.dump(state, open(path, "w"), indent=2)