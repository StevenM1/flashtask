#!/usr/bin/env python
# encoding: utf-8
from psychopy import visual
import numpy as np


class FlashStim(object):

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
        Draws the flashing circles. There are 3 options for continuous:
        0 : Draws the actual flashing circles
        1 : Draws constantly flashing circles (which always flash on every increment)
        2 : Draws constant white circles (no flashes anymore)

        Options 1 and 2 are possibilities for post-response stimulus drawing (to prevent an early "oh shit" response?)
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

# class FeedbackStim(object):
#
#     def __init__(self, screen, arguments=[]):
#         """
#         Assumes that arguments is a list of dictionaries with all arguments for each feedback type. Example:
#         >>> arguments = [{'text': 'Feedback type 1', 'col': (1, 0, 0)}, {'text': 'Feedback type 2', 'col': {0, 1, 0}]
#         """
#
#         self.screen = screen
#         self.feedback_objects = []
#
#         for i in range(len(arguments)):
#             self.feedback_objects.append(visual.TextStim(win=self.screen, units='cm', **arguments[i]))
#
#     def draw(self, feedback_type):
#
#         self.feedback_objects[feedback_type].draw()
