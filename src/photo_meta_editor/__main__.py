from __future__ import annotations

import multiprocessing
import sys
from pathlib import Path


if __name__ == "__main__":
    multiprocessing.freeze_support()

if __package__:
    from .app import main
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from photo_meta_editor.app import main


if __name__ == "__main__":
    main()
