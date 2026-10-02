"""The packaged ``scribe-host.exe``'s entry (installation plan Task 3.2): the
same ``scribe_desktop.native_host.main`` the source run's ``scribe-host``
launcher calls, nothing added (its stdio seam is Task 2.2's)."""

import sys

from scribe_desktop.native_host import main

sys.exit(main())
