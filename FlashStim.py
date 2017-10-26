#!/usr/bin/env python
# encoding: utf-8
from psychopy import visual
import numpy as np


class FlashStim(object):
    """
    Initializes and draws flashing circles stimuli.

    Parameters
    ----------
    screen: psychopy.visual.Window instance
    session: exp_tools.Session instance
    n_flashers: int
        Number of flashing circles to draw
    positions: list
        List of (x, y) tuples or [x, y] lists that determine the positions of each flashing circle on the screen in
        degrees.
    flasher_size: float
        Size of each circle in degrees.
    """
    def __init__(self, screen, session, n_flashers, positions, flasher_size):
        self.screen = screen
        self.session = session
        self.n_flashers = n_flashers
        self.trial_evidence_arrays = None
        self.shown_opacities = np.zeros(n_flashers)

        self.flasher_objects = []
        for i in range(self.n_flashers):
            self.flasher_objects.append(visual.Circle(win=self.screen, name='flasher_'+str(i), units='deg',
                                                      size=flasher_size, ori=0,
                                                      pos=positions[i], lineWidth=0, lineColor=[0, 0, 0],
                                                      lineColorSpace='rgb', fillColor=[1, 1, 1], fillColorSpace='rgb',
                                                      opacity=1, depth=-1.0, interpolate=True))

    def draw(self, frame_n, continuous=0):
        """
        Draws the flashing circles on the screen.

        Parameters
        ----------
        frame_n : int
            Current frame number. Is used to determine whether a 'flash' or a 'pause' should be shown (i.e.,
            opacity is 1 or 0, respectively).
        continuous: int [0, 1, 2]
            0: draws the actual flashing circles
            1: draws constantly flashing circles (each circle flashes on every increment)
            2: draws constant white circles (no flashes)
            Options 1 and 2 are possibilities for post-response stimulus drawing (to prevent an early
            "oh shit" response?)
        """

        if continuous == 1:
            # Show constant flashing; each circle flashes on every increment
            if frame_n % self.session.standard_parameters['increment_length'] <= self.session.standard_parameters['flash_length']:
                op = 1
            else:
                op = 0

            for i in range(self.n_flashers):
                self.flasher_objects[i].opacity = op
                self.flasher_objects[i].draw()

        elif continuous == 2:
            # Show constant white / no flashes
            for i in range(self.n_flashers):
                self.flasher_objects[i].opacity = 1
                self.flasher_objects[i].draw()

        else:
            if self.trial_evidence_arrays is None:
                raise(AttributeError('Oops! FlashStim does not have an evidence array yet... Did you initialize the '
                                     'FlashTrial correctly?'))
            # Real stimulus
            for i in range(self.n_flashers):
                self.shown_opacities[i] = self.trial_evidence_arrays[i][frame_n]
                self.flasher_objects[i].opacity = self.trial_evidence_arrays[i][frame_n]
                self.flasher_objects[i].draw()

            return self.shown_opacities