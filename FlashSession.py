from __future__ import division
from exp_tools import EyelinkSession
from psychopy import visual, event, monitors
import numpy as np
from standard_parameters import *
from warnings import warn

from FlashTrial import FlashTrial

class FlashSession(EyelinkSession):

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
        super(FlashSession, self).__init__(subject_initials, index_number, sound_system)

        screen = self.create_screen(size=screen_res, full_screen=1, physical_screen_distance=159.0,
                                    background_color=background_color, physical_screen_size=(70, 40),
                                    monitor=monitor_name)
        self.screen.monitor = monitors.Monitor(monitor_name)
        event.Mouse(visible=False, win=screen)

        self.create_output_file_name()
        if tracker_on:
            self.create_tracker(auto_trigger_calibration=1, calibration_type='HV9')
            if self.tracker_on:
                self.tracker_setup()
        else:
            self.create_tracker(tracker_on=False)

        self.response_keys = np.array(response_keys)  # converting to np.array allows for fancy indexing, useful later

        self.scanner = scanner      # either 'n' for no scanner, or a character with scanner pulse key, or 'simulate'
        # if self.scanner == 'simulate':
        #     from psychopy.hardware.emulator import launchScan
        #     self.scanner = launchScan(win=self.screen,
        #                               settings={'TR': 2.0, 'volumes': 100, 'sound': False, 'sync': 't'},
        #                               globalClock=self.clock)

        self.n_trials = n_trials    # specified in standard_parameters.py!
        self.standard_parameters = parameters

        # Initialize a bunch of attributes
        self.frame_rate = None
        self.correct_answers = None
        self.correct_keys = None
        self.incorrect_answers = None
        self.incorrect_keys = None
        self.trial_arrays = None

        # Initialize psychopy.visual objects attributes
        self.feedback_text_objects = None
        self.fixation_cross = None

        self.prepare_trials()

    def prepare_trials(self):

        # Prepare fixation cross
        self.fixation_cross = visual.TextStim(win=self.screen, text='+', font='', pos=(0.0, 0.0),
                                              depth=0, rgb=None, color=(1.0, 1.0, 1.0), colorSpace='rgb',
                                              opacity=1.0, contrast=1.0, units='pix', ori=0.0, height=30)

        # Prepare feedback stimuli
        self.feedback_text_objects = [
            visual.TextStim(win=self.screen, text='Too late!', color=(1, 100/255, 100/255), units='cm'),
            visual.TextStim(win=self.screen, text='Correct!', color=(100/255, 1, 100/255), units='cm'),
            visual.TextStim(win=self.screen, text='Wrong!', color=(1, 100/255, 100/255), units='cm')
        ]

        # Some shortcuts
        n_flashers = self.standard_parameters['n_flashers']
        radius = self.standard_parameters['radius']
        prop_correct = self.standard_parameters['prop_correct']
        prop_incorrect = self.standard_parameters['prop_incorrect']
        increment_length = self.standard_parameters['increment_length']
        flash_length = self.standard_parameters['flash_length']
        pause_length = increment_length - flash_length

        # Determine positions of flashers, simple trigonometry
        if n_flashers == 2:  # start from 0*pi (== (0,1)) if there are only two flashers (horizontal)
            t = 0
        else:                # else start from 0.5*pi (== (1,0))
            t = 0.5*np.pi

        pos_x = radius * np.cos(t + np.arange(1, n_flashers+1) * 2 * np.pi / n_flashers)
        pos_y = radius * np.sin(t + np.arange(1, n_flashers+1) * 2 * np.pi / n_flashers)
        self.flasher_positions = zip(pos_x, pos_y)

        # To calculate on which frames the flashers need to be (in)visible, first get frame rate of current monitor
        self.frame_rate = self.screen.getActualFrameRate()
        if self.frame_rate is None:
            warn('Could not automatically detect frame rate! Guessing it is 60...')
            self.frame_rate = 60
        self.frame_rate = np.round(self.frame_rate)  # Rounding to nearest integer

        # How many increments can we show during the stimulus period, with the specified increment_length and current
        # frame rate?
        n_increments = np.ceil(phase_durations[2] * self.frame_rate / increment_length).astype(int)

        # Knowing this, we can define an index mask to select all frames that correspond to the between-increment
        # pause period
        mask_idx = np.tile(np.hstack((np.repeat(0, repeats=flash_length),
                                      np.repeat(1, repeats=pause_length))),
                           n_increments).astype(bool)

        # Define which flashing circle is correct in all n_trials
        self.correct_answers = np.random.randint(low=0, high=n_flashers, size=n_trials)
        self.incorrect_answers = [np.delete(np.arange(n_flashers), i) for i in self.correct_answers]

        # Which key responses correspond to these flashers?
        self.correct_keys = np.array(self.response_keys)[self.correct_answers]
        self.incorrect_keys = [self.response_keys[self.incorrect_answers[i]] for i in range(n_trials)]

        # Initialize 'increment arrays' for correct and incorrect. These are arrays filled with 0s and 1s, determining
        # for each 'increment' whether a piece of evidence is shown or not.
        # (this is a bit loopy, but I can't be bothered to make nice matrices here)
        self.trial_arrays = []
        for trial_n in range(self.n_trials):

            evidence_streams_this_trial = []
            for i in range(n_flashers):

                # First, create initial evidence stream
                if i == self.correct_answers[trial_n]:
                    evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_correct, size=n_increments)
                else:
                    evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_incorrect, size=n_increments)

                # Repeat every increment for n_frames
                evidence_stream_this_flasher = np.repeat(evidence_stream_this_flasher, increment_length)
                evidence_stream_this_flasher[mask_idx] = 0   # add pause

                evidence_streams_this_trial.append(evidence_stream_this_flasher)

            self.trial_arrays.append(evidence_streams_this_trial)

    def run(self):

        for ID in range(self.n_trials):
            FlashTrial(ID=ID, parameters={'n_flashers': self.standard_parameters['n_flashers'],
                                          'flasher_size': self.standard_parameters['flasher_size'],
                                          'positions': self.flasher_positions,
                                          'trial_evidence_arrays': self.trial_arrays[ID],
                                          'correct_key': self.correct_keys[ID],
                                          'incorrect_keys': self.incorrect_keys[ID]},
                       phase_durations=phase_durations, session=self, screen=self.screen, tracker=self.tracker).run()

            if self.stopped:
                break
        self.close()

    # def stop(self):
    #     from pprint import pprint
    #     pprint(self.session.outputDict)
    #
    #     super(FlashSession, self).stop()
