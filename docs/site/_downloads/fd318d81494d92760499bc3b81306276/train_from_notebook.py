"""Run the canonical training notebook from the repository root.

The notebook remains the source of feature engineering and training logic. This
entry point runs its code cells in order without requiring a Jupyter server.
"""

from pathlib import Path
import os
import sys

import nbformat


REPO_ROOT = Path(__file__).resolve().parents[3]
NOTEBOOK = Path(__file__).with_name("unified.ipynb")


def main() -> None:
    os.chdir(REPO_ROOT)
    sys.path.insert(0, str(REPO_ROOT))
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    namespace = {"__name__": "__main__"}
    for index, cell in enumerate(notebook.cells, start=1):
        if cell.cell_type != "code" or not cell.source.strip():
            continue
        print(f"Running notebook cell {index}/{len(notebook.cells)}", flush=True)
        exec(compile(cell.source, f"{NOTEBOOK}:cell-{index}", "exec"), namespace)


if __name__ == "__main__":
    main()
