"""The packaged ``scribe-app.exe``'s entry (installation plan Task 3.2): the
same ``scribe_desktop.app.main`` the source run's ``scribe-app`` launcher
calls, nothing added."""

import sys

from scribe_desktop.app import main

sys.exit(main())
