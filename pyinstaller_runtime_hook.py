"""Initialize the working directory for frozen SoundRTS executables."""

import os
import sys


# SoundRTS resources intentionally live next to the executables and are
# addressed by relative paths throughout the application.
os.chdir(os.path.dirname(sys.executable))
