"""
Load strategies to use for trading
"""

import os
import importlib.util


def get_strategy(name):
    for dirpath, _, filenames in os.walk(os.path.dirname(__file__)):
        for filename in filenames:
            stem, ext = os.path.splitext(filename)
            stem = stem.strip()

            if ext != ".py" or (stem.startswith("__") and stem.endswith("__")) or stem != name:
                continue

            spec = importlib.util.spec_from_file_location(name, os.path.join(dirpath, filename))
            assert spec is not None
            assert spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.Strategy
    return None
