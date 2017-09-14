#!/usr/bin/env python
# encoding: utf-8
from __future__ import division
from exp_tools import EyelinkSession
from psychopy import visual, event, monitors, core, data, info
from standard_parameters import *
from warnings import warn
import pandas as pd
import os
import sys

from FlashTrial import *
from FlashInstructions import FlashInstructions
from FlashStim import FlashStim


class FlashSession(EyelinkSession):
    """
    Session of the "Flashing Circles" task with eye-tracking enabled.

    In this task, the participant is shown two flashing circles. Each circle has a predetermined probability of
    flashing at every time point. The task is to decide which circle flashes most often.

    Participants can either respond via keyboard or with a saccade.

    """

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
        super(FlashSession, self).__init__(subject_initials, index_number, sound_system)

        # Set-up screen
        screen = self.create_screen(size=screen_res, full_screen=1, physical_screen_distance=159.0,
                                    background_color=background_color, physical_screen_size=(70, 40),
                                    monitor=monitor_name)
        self.screen.monitor = monitors.Monitor(monitor_name)
        self.mouse = event.Mouse(win=screen, visible=False)

        # For logging: set-up output file name, experiment handler
        self.create_output_file_name()

        # Ensure that relative paths start from the same directory as this script
        _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
        self.exp_handler = data.ExperimentHandler(name='flashtask', version='0.1.0',
                                                  extraInfo={'subject_initials': subject_initials,
                                                             'index_number': index_number,
                                                             'scanner': scanner,
                                                             'tracker_on': tracker_on,
                                                             'manipulation': session_type},
                                                  runtimeInfo=info.RunTimeInfo,
                                                  dataFileName=os.path.join(_thisDir, self.output_file),
                                                  autoLog=True)
        self.trial_handler = None

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
        self.stimulus = None
        self.cue_object = None

        if response_type == 'keyboard':
            self.trial_pointer = FlashTrialKeyboard
            self.response_keys = np.array(response_keys)
        elif response_type == 'saccade':
            self.trial_pointer = FlashTrialSaccade

            # Radius for eye movement detection: 3 cm?
            self.eye_travel_threshold = 3

        self.prepare_trials()

    def prepare_trials(self):
        """
        Prepares everything necessary to run trials:

         - Fixation cross object (kept in FlashSession, not FlashTrial, for efficiency - no reinitalization every trial)
         - Feedback text objects (idem)
         - Flashing circles objects (idem)
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

        self.cue_object = visual.TextStim(win=self.screen, text='Cue here', units='cm')

        # Prepare feedback stimuli
        self.feedback_text_objects = [
            visual.TextStim(win=self.screen,  text='Too late!', color=(1, 100/255, 100/255), units='cm'),
            visual.TextStim(win=self.screen,  text='Correct!', color=(100/255, 1, 100/255), units='cm'),
            visual.TextStim(win=self.screen,  text='Wrong!', color=(1, 100/255, 100/255), units='cm'),
            visual.TextStim(win=self.screen,  text='Too fast!', color=(1, 100/255, 100/255), units='cm')
        ]

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

        # Prepare Flasher stimuli
        self.stimulus = FlashStim(screen=self.screen, session=self,
                                  n_flashers=self.n_flashers,
                                  flasher_size=self.flasher_size,
                                  positions=self.flasher_positions)

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
        mask_idx = np.tile(np.hstack((np.repeat([0], repeats=flash_length),
                                      np.repeat([1], repeats=pause_length))),
                           n_increments).astype(bool)

        # Define which flashing circle is correct in all n_trials
        if self.correct_answers is None:  # It might already be set by a subclass
            self.correct_answers = np.repeat([0, 1], repeats=n_trials/2)
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
                    evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_correct, size=n_increments).astype(
                        np.int8)
                else:
                    evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_incorrect,
                                                                      size=n_increments).astype(np.int8)

                # Repeat every increment for n_frames
                evidence_stream_this_flasher = np.repeat(evidence_stream_this_flasher, increment_length)
                evidence_stream_this_flasher[mask_idx] = 0   # add pause

                evidence_streams_this_trial.append(evidence_stream_this_flasher)

            self.trial_arrays.append(evidence_streams_this_trial)

        # Create new mask to select only first frame of every increment
        self.first_frame_idx = np.arange(0, mask_idx.shape[0], increment_length)

    def run(self):
        """ Run the trials that were prepared. The experimental design should be implemented here! """

        # Show instruction first
        FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
                          tracker=self.tracker).run()

        # Loop through trials
        for ID in range(self.n_trials):
            trial = self.trial_pointer(ID=ID, parameters={'trial_evidence_arrays': self.trial_arrays[ID],
                                                          'correct_answer': self.correct_answers[ID],
                                                          'incorrect_answers': self.incorrect_answers[ID]},
                                       phase_durations=phase_durations,
                                       session=self,
                                       screen=self.screen,
                                       tracker=self.tracker)
            trial.run()

            if self.stopped:
                break

        self.close()

    def close(self):
        self.exp_handler.saveAsPickle(self.exp_handler.dataFileName)
        self.exp_handler.saveAsWideText(self.exp_handler.dataFileName + '.csv')
        super(FlashSession, self).close()


class FlashSessionPayoffBias(FlashSession):
    """
    Subclasses FlashSession to handle an experimental session to a 3 x 2 (cue x correct) asymmetric pay-off bias design.

    Each trial has 6 phases:
    0. Fixation cross until scanner pulse
    1. Show cue (0.5s)
    2. Fixation cross (0.5s; this should be jittered)
    3. Stimulus presentation; participant can respond
    4. Stimulus presentation after participant has responded (until 1.5s has passed since phase 2)
    5. Feedback (0.5s)
    6. ITI (1s; this should be jittered)

    The cue is either 'NEU', 'LEFT', or 'RIGHT'. If the cue was NEU, any response (correct or incorrect) gets a
    pay-off of 0. If the cue was congruent with the correct answer, the participant receives 8 points for a correct
    answer. If the cue is incongruent with the correct answer, the participant receives 2 points for a correct
    answer. No points for too fast (<150ms), too late (>1.5s), or wrong answers.
    """

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
        super(FlashSessionPayoffBias, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system)

        self.trial_types = None
        self.cue_by_trial = None
        self.prepare_trials()
        self.participant_score = 0

    def prepare_trials(self):
        """
        Trial conditions are set up as follows:
        0. Neutral cue, left is correct. Pay-off: 0
        1. Neutral cue, right is correct. Pay-off: 0
        2. Left cue, left is correct. Pay-off: 8 if correct (0 if incorrect)
        3. Left cue, right is correct. Pay-off: 2 if correct (0 if incorrect)
        4. Right cue, left is correct. Pay-off: 2 if correct (0 if incorrect)
        5. Right cue, right is correct. Pay-off: 8 if correct (0 if incorrect)
        """

        self.trial_types = np.hstack((np.repeat([0, 1], repeats=n_trials/6),    # Neutral cue, left/right corr
                                      np.repeat([2, 3], repeats=n_trials/6),    # Left cue, left/right corr
                                      np.repeat([4, 5], repeats=n_trials/6)))   # Right cue, left/right corr
        np.random.shuffle(self.trial_types)

        if self.trial_types.shape[0] != n_trials:
            raise(ValueError('The provided n_trials (%d) could not be split into the correct number of trial types. '
                             'Closest option is %d trials' % (n_trials, self.trial_types.shape[0])))

        self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
        self.correct_answers = np.zeros(n_trials, dtype=np.int8)

        self.cue_by_trial[(self.trial_types == 0) | (self.trial_types == 1)] = 'NEU'
        self.cue_by_trial[(self.trial_types == 2) | (self.trial_types == 3)] = 'LEFT'
        self.cue_by_trial[(self.trial_types == 4) | (self.trial_types == 5)] = 'RIGHT'

        self.correct_answers[(self.trial_types == 0) |
                             (self.trial_types == 2) |
                             (self.trial_types == 4)] = 0  # 0 = left is correct
        self.correct_answers[(self.trial_types == 1) |
                             (self.trial_types == 3) |
                             (self.trial_types == 5)] = 1  # 1 = right is correct

        # Exported trial types to check whether everything went ok
        trial_data = pd.DataFrame({'ID': np.arange(n_trials),
                                   'correct_answer': self.correct_answers,
                                   'cue': self.cue_by_trial,
                                   'trial_types': self.trial_types})
        trial_data.to_csv(self.output_file + '_trial_types.csv', index=False)

        # Set-up trial handler
        self.trial_handler = data.TrialHandler(trial_data.to_dict('records'), 1, extraInfo=
                                               {'subject_initials': self.subject_initials,
                                                'index_number': self.index_number,
                                                'session_type': session_type,
                                                }, method='sequential')
        self.exp_handler.addLoop(self.trial_handler)

        super(FlashSessionPayoffBias, self).prepare_trials()

    def run(self):
        # Show instruction first
        FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
                          tracker=self.tracker).run()

        # Loop through trials
        for this_trial in self.trial_handler:
            this_ID = this_trial['ID']
            this_trial_type = this_trial['trial_type']
            this_cue = this_trial['cue']
            this_correct_answer = this_trial['correct_answer']
            this_trial_evidence_array = self.trial_arrays[this_ID]

            # Prepare feedback, in case the participant responds correctly
            if this_trial_type in [0, 1]:           # Neutral condition
                self.feedback_text_objects[1].text = 'Correct!'
            elif this_trial_type in [2, 5]:         # Compatible cue condition
                self.feedback_text_objects[1].text = 'Correct! +8\nTotal score: %d' % (self.participant_score+8)
            elif this_trial_type in [3, 4]:         # Incompatible cue condition
                self.feedback_text_objects[1].text = 'Correct! +2\nTotal score: %d' % (self.participant_score+2)

            trial = self.trial_pointer(ID=this_ID,
                                       parameters={'trial_evidence_arrays': this_trial_evidence_array,
                                                   'correct_answer': this_correct_answer,
                                                   'cue': this_cue,
                                                   'trial_type': this_trial_type},
                                       phase_durations=phase_durations,
                                       session=self,
                                       screen=self.screen,
                                       tracker=self.tracker)

            trial.run()

            # If the response given is correct, update scores
            if trial.response_type == 1:
                if this_trial_type in [2, 5]:
                    self.participant_score += 8
                elif this_trial_type in [3, 4]:
                    self.participant_score += 2

            # Add all data
            self.trial_handler.addData('rt', trial.response_time)
            self.trial_handler.addData('response', trial.response)
            self.trial_handler.addData('correct', trial.response_type == 1)
            for flasher in range(self.n_flashers):
                self.trial_handler.addData('evidence stream ' + str(flasher),
                                           this_trial_evidence_array[flasher][self.first_frame_idx])

            self.trial_handler.addData('evidence shown at rt',
                                       trial.evidence_shown/self.standard_parameters['flash_length'])
            self.exp_handler.nextEntry()

            if self.stopped:
                break

        self.close()


class FlashSessionSAT(FlashSession):
    """
    Subclasses FlashSession to handle an experimental session to a 2 x 2 (cue x correct) speed-accuracy trade-off
    design.

    Each trial has 6 phases:
    0. Fixation cross until scanner pulse
    1. Show cue (0.5s)
    2. Fixation cross (0.5s; this should be jittered)
    3. Stimulus presentation; participant can respond
    4. Stimulus presentation after participant has responded (until 1.5s has passed since phase 2)
    5. Feedback (0.5s)
    6. ITI (1s; this should be jittered)

    The cue is either 'SP', or 'ACC'.
    """

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
        super(FlashSessionSAT, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system)

        self.trial_types = None
        self.cue_by_trial = None
        self.prepare_trials()

    def prepare_trials(self):
        """
        """

        self.trial_types = np.hstack(
            (np.repeat([0, 1], repeats=n_trials / 4),   # SPEED cue, left/right corr
             np.repeat([2, 3], repeats=n_trials / 4)))  # ACCURACY cue, left/right corr

        np.random.shuffle(self.trial_types)

        if self.trial_types.shape[0] != n_trials:
            raise(ValueError('The provided n_trials (%d) could not be split into the correct number of trial types. '
                             'Closest option is %d trials' % (n_trials, self.trial_types.shape[0])))

        self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
        self.correct_answers = np.zeros(n_trials, dtype=np.int8)

        self.cue_by_trial[(self.trial_types == 0) | (self.trial_types == 1)] = 'SP'
        self.cue_by_trial[(self.trial_types == 2) | (self.trial_types == 3)] = 'ACC'

        self.correct_answers[(self.trial_types == 0) |
                             (self.trial_types == 2)] = 0  # 0 = left is correct
        self.correct_answers[(self.trial_types == 1) |
                             (self.trial_types == 3)] = 1  # 1 = right is correct

        # Exported trial types to check whether everything went ok
        trial_data = pd.DataFrame({'ID': np.arange(n_trials),
                                   'correct_answer': self.correct_answers,
                                   'cue': self.cue_by_trial,
                                   'trial_type': self.trial_types})
        trial_data.to_csv(self.output_file + '_trial_types.csv', index=False)

        # Set-up trial handler
        self.trial_handler = data.TrialHandler(trial_data.to_dict('records'), 1,
                                               extraInfo={'subject_initials': self.subject_initials,
                                                          'index_number': self.index_number,
                                                          'session_type': session_type,
                                                          },
                                               method='sequential')
        self.exp_handler.addLoop(self.trial_handler)

        super(FlashSessionSAT, self).prepare_trials()

    def run(self):
        # Show instruction first
        FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
                          tracker=self.tracker).run()

        # Loop through trials
        for this_trial in self.trial_handler:
            this_ID = this_trial['ID']
            this_trial_type = this_trial['trial_type']
            this_cue = this_trial['cue']
            this_correct_answer = this_trial['correct_answer']
            this_trial_evidence_array = self.trial_arrays[this_ID]

            trial = self.trial_pointer(ID=this_ID,
                                       parameters={'trial_evidence_arrays': this_trial_evidence_array,
                                                   'correct_answer': this_correct_answer,
                                                   'cue': this_cue,
                                                   'trial_type': this_trial_type},
                                       phase_durations=phase_durations,
                                       session=self,
                                       screen=self.screen,
                                       tracker=self.tracker)
            trial.run()

            # Add all data
            self.trial_handler.addData('rt', trial.response_time)
            self.trial_handler.addData('response', trial.response)
            self.trial_handler.addData('correct', trial.response_type == 1)

            for flasher in range(self.n_flashers):
                self.trial_handler.addData('evidence stream ' + str(flasher),
                                           this_trial_evidence_array[flasher][self.first_frame_idx])
            self.trial_handler.addData('evidence shown at rt',
                                       trial.evidence_shown/self.standard_parameters['flash_length'])

            self.exp_handler.nextEntry()

            if self.stopped:
                break

        self.close()


class FlashSessionMotor(FlashSession):
    """
    Subclasses FlashSession to handle an experimental session to a 2 x 2 (cue x correct) speed-accuracy trade-off
    design.

    Each trial has 6 phases:
    0. Fixation cross until scanner pulse
    1. Show cue (0.5s)
    2. Fixation cross (0.5s; this should be jittered)
    3. Stimulus presentation; participant can respond
    4. Stimulus presentation after participant has responded (until 1.5s has passed since phase 2)
    5. Feedback (0.5s)
    6. ITI (1s; this should be jittered)

    The cue is either 'eye', or 'hand'.
    """

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
        super(FlashSessionMotor, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system)

        # These are not set correctly for this manipulation
        self.response_keys = np.array(response_keys)
        self.eye_travel_threshold = 3
        self.trial_pointer = None

        self.trial_types = None
        self.cue_by_trial = None
        self.prepare_trials()

    def prepare_trials(self):
        """
        """

        self.trial_types = np.hstack(
            (np.repeat([0, 1], repeats=n_trials / 4),   # EYE cue, left/right corr
             np.repeat([2, 3], repeats=n_trials / 4)))  # HAND cue, left/right corr

        np.random.shuffle(self.trial_types)

        if self.trial_types.shape[0] != n_trials:
            raise (
                ValueError(
                    'The provided n_trials (%d) could not be split into the correct number of trial types. '
                    'Closest option is %d trials' % (n_trials, self.trial_types.shape[0])))

        self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
        self.correct_answers = np.zeros(n_trials, dtype=np.int8)

        self.cue_by_trial[(self.trial_types == 0) | (self.trial_types == 1)] = 'EYE'
        self.cue_by_trial[(self.trial_types == 2) | (self.trial_types == 3)] = 'HAND'

        self.correct_answers[(self.trial_types == 0) |
                             (self.trial_types == 2)] = 0  # 0 = left is correct
        self.correct_answers[(self.trial_types == 1) |
                             (self.trial_types == 3)] = 1  # 1 = right is correct

        # Exported trial types to check whether everything went ok
        trial_data = pd.DataFrame({'ID': np.arange(n_trials),
                                   'correct_answer': self.correct_answers,
                                   'cue': self.cue_by_trial,
                                   'trial_type': self.trial_types})
        trial_data.to_csv(self.output_file + '_trial_types.csv', index=False)

        # Set-up trial handler
        self.trial_handler = data.TrialHandler(trial_data.to_dict('records'), 1,
                                               extraInfo={'subject_initials': self.subject_initials,
                                                          'index_number': self.index_number,
                                                          'session_type': session_type,
                                                          },
                                               method='sequential')
        self.exp_handler.addLoop(self.trial_handler)

        super(FlashSessionMotor, self).prepare_trials()

    def run(self):
        # Show instruction first
        FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
                          tracker=self.tracker).run()

        # Loop through trials
        for this_trial in self.trial_handler:
            this_ID = this_trial['ID']
            this_trial_type = this_trial['trial_type']
            this_cue = this_trial['cue']
            this_correct_answer = this_trial['correct_answer']
            this_trial_evidence_array = self.trial_arrays[this_ID]

            if this_cue == 'EYE':
                trial_pointer = FlashTrialSaccade
            elif this_cue == 'HAND':
                trial_pointer = FlashTrialKeyboard
            else:
                raise(ValueError('Something is wrong: cue type not understood; should be EYE or HAND'))

            trial = trial_pointer(ID=this_ID,
                                  parameters={'trial_evidence_arrays': this_trial_evidence_array,
                                              'correct_answer': this_correct_answer,
                                              'cue': this_cue,
                                              'trial_type': this_trial_type},
                                  phase_durations=phase_durations,
                                  session=self,
                                  screen=self.screen,
                                  tracker=self.tracker)
            trial.run()

            # Add all data
            self.trial_handler.addData('rt', trial.response_time)
            self.trial_handler.addData('response', trial.response)
            self.trial_handler.addData('correct', trial.response_type == 1)

            for flasher in range(self.n_flashers):
                self.trial_handler.addData('evidence stream ' + str(flasher),
                                           this_trial_evidence_array[flasher][self.first_frame_idx])

            self.trial_handler.addData('evidence shown at rt',
                                       trial.evidence_shown/self.standard_parameters['flash_length'])

            self.exp_handler.nextEntry()

            if self.stopped:
                break

        self.close()

# class FlashSessionProbBias(FlashSession):
#
#     def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
#         super(FlashSessionProbBias, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system)
#
#         self.trial_conditions = None
#         self.cue_by_trial = None
#         self.prepare_trials()
#
#     def prepare_trials(self):
#
#         self.trial_conditions = np.hstack((np.repeat([0, 1], repeats=n_trials/4),  # Neutral trials, left/right corr
#                                            np.repeat([2, 3], repeats=(n_trials/4)*.8),  # Bias left/right: correct
#                                            np.repeat([4, 5], repeats=(n_trials/4)*.2)))  # Bias left/right: incorrect
#         np.random.shuffle(self.trial_conditions)
#
#         if self.trial_conditions.shape[0] != n_trials:
#             raise(ValueError('The provided n_trials (%d) could not be split into the correct number of trial types. '
#                              'Closest option is %d trials' % (n_trials, self.trial_conditions.shape[0])))
#
#         self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
#         self.correct_answers = np.zeros(n_trials, dtype=np.int8)
#
#         self.cue_by_trial[(self.trial_conditions == 0) | (self.trial_conditions == 1)] = 'NEU'
#         self.cue_by_trial[(self.trial_conditions == 2) | (self.trial_conditions == 4)] = 'LEFT'
#         self.cue_by_trial[(self.trial_conditions == 3) | (self.trial_conditions == 5)] = 'RIGHT'
#
#         self.correct_answers[(self.trial_conditions == 0) |
#                              (self.trial_conditions == 2) |
#                              (self.trial_conditions == 5)] = 0
#         self.correct_answers[(self.trial_conditions == 1) |
#                              (self.trial_conditions == 3) |
#                              (self.trial_conditions == 4)] = 1
#
#         # tmp: exported trial types to check whether everything went ok
#         # import pandas as pd
#         # trial_data = pd.DataFrame({'correct_answer': self.correct_answers,
#         #                            'cue': self.cue_by_trial,
#         #                            'trial_condition': self.trial_conditions})
#         # trial_data.to_csv('/users/steven/Desktop/trial_conditions.csv')
#
#         super(FlashSessionProbBias, self).prepare_trials()
#
#     def run(self):
#
#         # Show instruction first
#         FlashInstructions(ID=-1, parameters={'instruction_text': "Decide which circle flashes most"},
#                           phase_durations=[100],
#                           session=self,
#                           screen=self.screen,
#                           tracker=self.tracker).run()
#
#         # Loop through trials
#         for ID in range(self.n_trials):
#             FlashTrialKeyboard(ID=ID, parameters={'trial_evidence_arrays': self.trial_arrays[ID],
#                                                   'correct_answer': self.correct_answers[ID],
#                                                   'incorrect_answers': self.incorrect_answers[ID],
#                                                   'cue': self.cue_by_trial[ID]},
#                                phase_durations=phase_durations,
#                                session=self,
#                                screen=self.screen,
#                                tracker=self.tracker).run()
#
#             if self.stopped:
#                 break
#
#         self.close()
#
