# These are constants used for PyGaze. Note that these are automatically calculated using the values entered in
# standard_parameters and Monitor - no need to edit anything here.

from __future__ import division
from psychopy.monitors import Monitor
from standard_parameters import monitor_name

mon = Monitor(monitor_name)
mon_width = mon.getWidth()
mon_size_pix = mon.getSizePix()
mon_height = mon_size_pix[1] * mon_width / mon_size_pix[0]

SCREENSIZE = (mon_width, mon_height)
DISPSIZE = (int(mon_size_pix[0]), int(mon_size_pix[1]))
