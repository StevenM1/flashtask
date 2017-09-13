from __future__ import division
from exp_tools import EyelinkSession
import pygaze
from psychopy import visual, event, monitors, core
import numpy as np
from standard_parameters import *
from warnings import warn

from FlashTrial import *
from FlashInstructions import FlashInstructions


class FlashSession(EyelinkSession):
    """
    Session of the "Flashing Circles" task with eye-tracking enabled.

    """

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
        super(FlashSession, self).__init__(subject_initials, index_number, sound_system)

        # Set-up screen
        screen = self.create_screen(size=screen_res, full_screen=1, physical_screen_distance=159.0,
                                    background_color=background_color, physical_screen_size=(70, 40),
                                    monitor=monitor_name)
        self.screen.monitor = monitors.Monitor(monitor_name)
        self.mouse = event.Mouse(win=screen, visible=False)

        # For logging: set-up output file name
        self.create_output_file_name()

        # Set-up eye tracker OR dummy
        if tracker_on:
            self.create_tracker(auto_trigger_calibration=1, calibration_type='HV9')

            if self.tracker_on:  # If it found an Eyelink tracker connected, set it up
                self.dummy_tracker = False
                self.tracker_setup()
            else:                # If no tracker is found, use mouse as dummy tracker
                self.dummy_tracker = True
                self.screen.setMouseVisible(True)
        else:
            self.create_tracker(tracker_on=False)

        self.response_keys = np.array(response_keys)  # converting to np.array allows for fancy indexing, useful later
        self.scanner = scanner      # either 'n' for no scanner, or a character with scanner pulse key
        self.n_trials = n_trials    # specified in standard_parameters.py!
        self.standard_parameters = parameters

        # Initialize a bunch of attributes used in prepare_trials()
        self.frame_rate = None
        self.correct_answers = None  # integer vector corresponding to the flasher number
        self.correct_responses = None  # either a key ('z', 'm') or a direction ('left', 'right')
        self.incorrect_answers = None
        self.incorrect_responses = None
        self.trial_arrays = None
        self.flasher_positions = None

        # Get session information about flashers
        self.n_flashers = self.standard_parameters['n_flashers']
        self.radius = self.standard_parameters['radius']
        self.flasher_size = self.standard_parameters['flasher_size']

        # Initialize psychopy.visual objects attributes
        self.feedback_text_objects = None
        self.fixation_cross = None

        self.prepare_trials()

    def prepare_trials(self):
        """
        Prepares everything necessary to run trials:

         - Fixation cross object (kept in FlashSession, not FlashTrial, for efficiency - no reinitalization for every trial)
         - Feedback text objects (idem)
         - Determines the position on the screen that is recognized as a "response" in the saccadic response condition
         - Correct answers (integer), correct keys, incorrect answers, incorrect keys per trial
         - Positions of flashing circles
         - Evidence stream per flashing circle per trial
         - Opacity-per-frame for all flashing circles for all trials.
         """

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

        # Radius for eye movement detection: 3 cm? # ToDo: think about this: where to place this?
        self.eye_travel_threshold = 3

        # Some shortcuts
        prop_correct = self.standard_parameters['prop_correct']
        prop_incorrect = self.standard_parameters['prop_incorrect']
        increment_length = self.standard_parameters['increment_length']
        flash_length = self.standard_parameters['flash_length']
        pause_length = increment_length - flash_length

        # Determine positions of flashers, simple trigonometry
        if self.n_flashers == 2:  # start from 0*pi (== (0,1)) if there are only two flashers (horizontal)
            t = 0
        else:                # else start from 0.5*pi (== (1,0))
            t = 0.5*np.pi

        pos_x = self.radius * np.cos(t + np.arange(1, self.n_flashers+1) * 2 * np.pi / self.n_flashers)
        pos_y = self.radius * np.sin(t + np.arange(1, self.n_flashers+1) * 2 * np.pi / self.n_flashers)
        self.flasher_positions = zip(pos_x, pos_y)

        # To calculate on which frames the flashers need to be (in)visible, first get frame rate of current monitor
        self.frame_rate = self.screen.getActualFrameRate()
        if self.frame_rate is None:
            warn('Could not automatically detect frame rate! Guessing it is 60...')
            self.frame_rate = 60
        self.frame_rate = np.round(self.frame_rate)  # Rounding to nearest integer

        # How many increments can we show during the stimulus period, with the specified increment_length and current
        # frame rate?
        n_increments = np.ceil(phase_durations[3] * self.frame_rate / increment_length).astype(int)

        # Knowing this, we can define an index mask to select all frames that correspond to the between-increment
        # pause period
        mask_idx = np.tile(np.hstack((np.repeat(0, repeats=flash_length),
                                      np.repeat(1, repeats=pause_length))),
                           n_increments).astype(bool)

        # Define which flashing circle is correct in all n_trials
        if self.correct_answers is None:  # It might already be set by a subclass
            self.correct_answers = np.repeat([0, 1], repeats=n_trials/2)   # np.random.randint(low=0, high=n_flashers, size=n_trials)
            np.random.shuffle(self.correct_answers)
        self.incorrect_answers = [np.delete(np.arange(self.n_flashers), i) for i in self.correct_answers]

        # # Which responses (keys or saccades) correspond to these flashers?
        # self.correct_responses = np.array(self.response_keys)[self.correct_answers]
        # self.incorrect_responses = [self.response_keys[self.incorrect_answers[i]] for i in range(n_trials)]

        # Initialize 'increment arrays' for correct and incorrect. These are arrays filled with 0s and 1s, determining
        # for each 'increment' whether a piece of evidence is shown or not.
        # (this is a bit loopy, but I can't be bothered to make nice matrices here)
        self.trial_arrays = []
        for trial_n in range(self.n_trials):

            evidence_streams_this_trial = []
            for i in range(self.n_flashers):

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
        """ Run the trials that were prepared. The experimental design should be implemented here! """

        # Show instruction first
        FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
                          tracker=self.tracker).run()

        # Loop through trials
        for ID in range(self.n_trials):
            FlashTrialKeyboard(ID=ID, parameters={'trial_evidence_arrays': self.trial_arrays[ID],
                                                  'correct_answer': self.correct_answers[ID],
                                                  'incorrect_answers': self.incorrect_answers[ID]},
                               phase_durations=phase_durations,
                               session=self,
                               screen=self.screen,
                               tracker=self.tracker).run()

            if self.stopped:
                break

        self.close()


class FlashSessionProbBias(FlashSession):

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
        super(FlashSessionProbBias, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system=False)

        self.trial_conditions = None
        self.cue_by_trial = None
        self.prepare_trials()

    def prepare_trials(self):

        self.trial_conditions = np.hstack((np.repeat([0, 1], repeats=n_trials/4),  # Neutral trials, left/right corr
                                           np.repeat([2, 3], repeats=(n_trials/4)*.8),  # Bias left/right: correct
                                           np.repeat([4, 5], repeats=(n_trials/4)*.2)))  # Bias left/right: incorrect
        np.random.shuffle(self.trial_conditions)

        if self.trial_conditions.shape[0] != n_trials:
            raise(ValueError('The provided n_trials (%d) could not be split into the correct number of trial types. '
                             'Closest option is %d trials' % (n_trials, self.trial_conditions.shape[0])))

        self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
        self.correct_answers = np.zeros(n_trials, dtype=np.int)

        self.cue_by_trial[(self.trial_conditions == 0) | (self.trial_conditions == 1)] = 'NEU'
        self.cue_by_trial[(self.trial_conditions == 2) | (self.trial_conditions == 4)] = 'LEFT'
        self.cue_by_trial[(self.trial_conditions == 3) | (self.trial_conditions == 5)] = 'RIGHT'

        self.correct_answers[(self.trial_conditions == 0) |
                             (self.trial_conditions == 2) |
                             (self.trial_conditions == 5)] = 0
        self.correct_answers[(self.trial_conditions == 1) |
                             (self.trial_conditions == 3) |
                             (self.trial_conditions == 4)] = 1

        # tmp: exported trial types to check whether everything went ok
        # import pandas as pd
        # trial_data = pd.DataFrame({'correct_answer': self.correct_answers,
        #                            'cue': self.cue_by_trial,
        #                            'trial_condition': self.trial_conditions})
        # trial_data.to_csv('/users/steven/Desktop/trial_conditions.csv')

        super(FlashSessionProbBias, self).prepare_trials()

    def run(self):

        # Show instruction first
        FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
                          tracker=self.tracker).run()

        # Loop through trials
        for ID in range(self.n_trials):
            FlashTrialKeyboard(ID=ID, parameters={'trial_evidence_arrays': self.trial_arrays[ID],
                                                  'correct_answer': self.correct_answers[ID],
                                                  'incorrect_answers': self.incorrect_answers[ID],
                                                  'cue': self.cue_by_trial[ID]},
                               phase_durations=phase_durations,
                               session=self,
                               screen=self.screen,
                               tracker=self.tracker).run()

            if self.stopped:
                break

        self.close()

