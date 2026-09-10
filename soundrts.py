#! .venv\Scripts\python.exe
import sys

# External updater must start before pygame / menu init.
if "--soundrts-update" in sys.argv:
    from soundrts.update_window import main as update_main

    raise SystemExit(update_main())

from soundrts import clientmain

clientmain.main()
