#!/usr/bin/env python
# encoding: utf-8
from __future__ import division
from exp_tools import EyelinkSession
from psychopy import visual, event, monitors, core, data, info
from standard_parameters import *
from warnings import warn
import pylab
import pandas as pd
import os
import sys
from glob import glob

from FlashTrial import *
from FlashInstructions import FlashInstructions
from FlashStim import FlashStim
from LocalizerTrial import *
from NullTrial import *
from FixationCross import *


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
        self.exp_handler = data.ExperimentHandler(name='flashtask',
                                                  version='0.2.0',
                                                  extraInfo={'subject_initials': subject_initials,
                                                             'index_number': index_number,
                                                             'scanner': scanner,
                                                             'tracker_on': tracker_on},
                                                  runtimeInfo=info.RunTimeInfo,
                                                  dataFileName=os.path.join(_thisDir, self.output_file),
                                                  autoLog=True)
        self.trial_handlers = []
        self.participant_scores = []

        # If we're running in debug mode, only show the instruction screens for 1 sec each.
        if self.subject_initials == 'DEBUG':
            self.instructions_durations = [1]
        else:
            # Otherwise show them for maximum 10 minutes (the user should skip screens).
            self.instructions_durations = [600]

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
        self.standard_parameters = parameters

        # Initialize a bunch of attributes used in load_design() or prepare_trials()
        self.n_trials = None
        self.stim_max_time = None
        self.frame_rate = None
        self.design = None
        self.correct_answers = None  # integer vector corresponding to the flasher number
        self.correct_responses = None  # either a key ('z', 'm') or a direction ('left', 'right')
        self.incorrect_answers = None
        self.incorrect_responses = None
        self.trial_arrays = None
        self.flasher_positions = None
        self.first_frame_idx = None

        # Get session information about flashers
        self.n_flashers = self.standard_parameters['n_flashers']
        self.radius = self.standard_parameters['radius']
        self.flasher_size = self.standard_parameters['flasher_size']

        # Initialize psychopy.visual objects attributes
        self.feedback_text_objects = None
        self.fixation_cross = None
        self.stimulus = None
        self.cue_object = None
        self.arrow_stimuli = None
        self.scanner_wait_screen = None
        self.localizer_instructions = None
        self.cognitive_eye_instructions = None
        self.cognitive_hand_instructions = None
        self.limbic_eye_instructions = None
        self.limbic_hand_instructions = None
        self.welcome_screen = None
        self.current_instruction = None
        self.instructions_to_show = None

        self.response_keys = np.array(response_keys)

        # Radius for eye movement detection: 3 cm?
        self.eye_travel_threshold = 3

        # Load design and prepare all trials
        self.block_types = []
        self.load_design()
        self.prepare_visual_objects()
        self.prepare_trials()

    def load_design(self):
        """ Loads all trials (blocks, conditions). The design files are created in a separate notebook. """

        # useful shortcut
        pp_dir = 'pp_%s' % str(self.index_number).zfill(3)

        # Load full design in self.design
        self.design = pd.read_csv(os.path.join(design_path, pp_dir, 'all_blocks', 'trials.csv'))

        # Get the number of trials from the design; this is the the number of rows in the DataFrame.
        self.n_trials = self.design.shape[0]
        self.stim_max_time = self.design['phase_4'].max()  # Also get the maximum duration a stimulus is shown

        # Make sure the correct_answers are extracted from the design
        self.correct_answers = self.design['correct_answer'].values
        self.correct_answers = self.correct_answers.astype(int)

        # First load localizer block
        localizer_conditions = data.importConditions(
            os.path.join(design_path, pp_dir, 'block_0_type_localizer', 'trials.csv'))

        # Append the localizer trial handler to the self.trial_handlers attr
        self.trial_handlers.append(data.TrialHandler(localizer_conditions, nReps=1, method='sequential'))

        # Loop over the four blocks and add them, as trial handlers, to the experiment handler
        for block in range(4):

            # Find path of block design
            path = glob(os.path.join(design_path, pp_dir, 'block_%d_*' % (block+1), 'trials.csv'))[0]

            # Create trial handler, and append to experiment handler
            self.trial_handlers.append(data.TrialHandler(data.importConditions(path), nReps=1, method='sequential'))

        # Make sure to add all trial handlers to the experiment handler
        for trial_handler in self.trial_handlers:
            self.exp_handler.addLoop(trial_handler)

    def prepare_visual_objects(self):
        """
        Prepares all visual objects necessary, except for the flashing stimuli (these are prepared in prepare_trials()):
        - Fixation cross object (kept in FlashSession, not FlashTrial, for efficiency - no reinitalization every trial)
        - Cue object
        - Feedback text objects (idem)
        - Localizer stimuli (idem)
        - Instruction screens (idem)
        """

        # Prepare fixation cross
        self.fixation_cross = FixationCross(win=self.screen, rad=0.3, bg=background_color)

        # Prepare cue
        self.cue_object = visual.TextStim(win=self.screen, text='Cue here', units='cm')

        # Prepare feedback stimuli
        self.feedback_text_objects = [
            visual.TextStim(win=self.screen, text='Too late!', color=(1, 100/255, 100/255), units='cm'),
            visual.TextStim(win=self.screen, text='Correct!', color=(100/255, 1, 100/255), units='cm'),
            visual.TextStim(win=self.screen, text='Wrong!', color=(1, 100/255, 100/255), units='cm'),
            visual.TextStim(win=self.screen, text='Too fast!', color=(1, 100/255, 100/255), units='cm')
        ]

        # Prepare localizer stimuli
        arrow_right_vertices = [(-0.2, 0.05), (-0.2, -0.05), (-.0, -0.05), (0, -0.1), (0.2, 0), (0, 0.1), (0, 0.05)]
        arrow_left_vertices = [(0.2, 0.05), (0.2, -0.05), (0.0, -0.05), (0, -0.1), (-0.2, 0), (0, 0.1), (0, 0.05)]
        arrow_neutral_vertices = [(0.3, 0.0),  # Right point
                                  (0.1, 0.1),  # Towards up, left
                                  (0.1, 0.05),  # Down
                                  (-0.1, 0.05),  # Left
                                  (-0.1, 0.1),  # Up
                                  (-0.3, 0.0),  # Left point
                                  (-0.1, -0.1),  # Down, right
                                  (-0.1, -0.05),  # Up
                                  (0.1, -0.05),  # Right
                                  (0.1, -0.1)]  # Down

        self.arrow_stimuli = [
            visual.ShapeStim(win=self.screen, vertices=arrow_left_vertices, fillColor='lightgray', size=.25,
                             lineColor='white', units='height'),
            visual.ShapeStim(win=self.screen, vertices=arrow_right_vertices, fillColor='lightgray', size=.25,
                             lineColor='white', units='height'),
            visual.ShapeStim(win=self.screen, vertices=arrow_neutral_vertices, fillColor='lightgray', size=.25,
                             lineColor='white', units='height')
        ]

        # Prepare waiting for scanner-screen
        self.scanner_wait_screen = visual.TextStim(win=self.screen,
                                              text='Waiting for scanner...',
                                              units='pix', font='Helvetica Neue', pos=(0, 0),
                                              italic=False, height=30, alignHoriz='center',)

        # Keep debug screen at hand
        self.debug_screen = visual.TextStim(win=self.screen,
                                            text='DEBUG MODE. DO NOT RUN AN ACTUAL EXPERIMENT',
                                            color='darkred', height=1, units='cm')

        # Prepare welcome screen
        self.welcome_screen = visual.TextStim(win=self.screen,
                                              text='Welcome to this experiment!\n\nPress '
                                                   'a button to continue',
                                              units='pix', font='Helvetica Neue', pos=(0, 0),
                                              italic=False, height=30, alignHoriz='center',)

        # Prepare instruction screens
        self.localizer_instructions = [
            visual.TextStim(win=self.screen, text='In the next trials, you will first read a cue that tells you how '
                                                  'to respond: either by making an eye movement, '
                                                  'or by pressing a button.\n\nAfterwards, you see an arrow. '
                                                  'When you see the arrow, respond as fast as possible. If the cue '
                                                  'was EYE, make an eye movement in the direction that was indicated '
                                                  'by the arrow. If the cue was HAND, press the left or right button, '
                                                  'as indicated by the arrow.\n\nPress a button to continue',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='Always respond as fast as possible, without making '
                                                  'mistakes!\n\nPress a button to start',
                            font='Helvetica Neue', pos=(0, 0), italic=False, height=30, alignHoriz='center',
                            units='pix')
        ]

        self.cognitive_eye_instructions = [
            visual.TextStim(win=self.screen, text='In the next trials, you need to decide which of two '
                                                  'circles flashes most often. If the left circle flashes most often, '
                                                  'look towards the left side of the screen. If the right circle '
                                                  'flashes most often, look towards the right side of the screen.\n\n'
                                                  'Before each trial, you receive a cue that tells you either to '
                                                  'respond as fast as possible (SPD), or as accurate as possible ('
                                                  'ACC). \n\nPress a button to continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='Remember to respond with your eyes!\n\nPress a button to start',
                            font='Helvetica Neue', pos=(0, 0), italic=False, height=30, alignHoriz='center',
                            units='pix')
        ]

        self.cognitive_hand_instructions = [
            visual.TextStim(win=self.screen, text='In the next trials, you need to decide which of two '
                                                  'circles flashes most often. If the left circle flashes most often, '
                                                  'press the button in your left hand. If the right circle '
                                                  'flashes most often, press the button in your right hand.\n\n'
                                                  'Before each trial, you receive a cue that tells you either to '
                                                  'respond as fast as possible (SPD), or as accurate as possible ('
                                                  'ACC). \n\nPress a button to continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='Remember to respond with your hands!\n\nPress a button to start',
                            font='Helvetica Neue', pos=(0, 0), italic=False, height=30, alignHoriz='center',
                            units='pix')
        ]

        self.limbic_eye_instructions = [
            visual.TextStim(win=self.screen, text='In the next trials, you need to decide which of two '
                                                  'circles flashes most often. If the left circle flashes most often, '
                                                  'look towards the left side of the screen. If the right circle '
                                                  'flashes most often, look towards the right side of the screen.\n\n'
                                                  'Press a button to continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='You earn points by answering correctly. At the end of the '
                                                  'experiment, you will receive a monetary reward depending on how '
                                                  'many points you earn. For each correct answer, '
                                                  'you receive either 0, 2, or 8 points, depending on the cue at the '
                                                  'start of the trial.\n\nPress a button to continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='The cue-arrow indicates for which answer (left or right) you get 8 '
                                                  'points, if you get it correct. For example, if the cue-arrow '
                                                  'points to the left, and you correctly answer left, '
                                                  'you get 8 points. However, if the cue-arrow points to the left, '
                                                  'and the correct answer is right, you get 2 points if you answer '
                                                  'right - you never get points for wrong answers!\n\nIf the cue '
                                                  'points in both directions, you will not receive points, '
                                                  'but you must still answer correctly.\n\nPress a button to '
                                                  'continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='Every time you earn points, you will see how many points you '
                                                  'earned, and how many points you earned in total for this block.\n\n'
                                                  'Remember to respond with your eyes!\n\nPress a button to start',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix')
        ]

        self.limbic_hand_instructions = [
            visual.TextStim(win=self.screen, text='In the next trials, you need to decide which of two '
                                                  'circles flashes most often. If the left circle flashes most often, '
                                                  'press the button in your left hand. If the right circle '
                                                  'flashes most often, press the button in your right hand.\n\n'
                                                  'Press a button to continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='You earn points by answering correctly. At the end of the '
                                                  'experiment, you will receive a monetary reward depending on how '
                                                  'many points you earn. For each correct answer, '
                                                  'you receive either 2 or 8 points, depending on the cue at the '
                                                  'start of the trial.\n\nPress a button to continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='The cue-arrow indicates for which answer (left or right) you get 8 '
                                                  'points, if you get it correct. For example, if the cue-arrow '
                                                  'points to the left, and you correctly answer left, '
                                                  'you get 8 points. However, if the cue-arrow points to the left, '
                                                  'and the correct answer is right, you get 2 points if you answer '
                                                  'right - you never get points for wrong answers!\n\nIf the cue '
                                                  'points in both directions, you will not receive points, '
                                                  'but you must still answer correctly.\n\nPress a button to '
                                                  'continue to next screen',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix'),
            visual.TextStim(win=self.screen, text='Every time you earn points, you will see how many points you '
                                                  'earned, and how many points you earned in total for this block.\n\n'
                                                  'Remember to respond with your hands!\n\nPress a button to start',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix')
        ]

    def prepare_trials(self):
        """
        Prepares everything necessary to run trials:
         - Flashing circles objects (kept in FlashSession for efficiency)
         - Determines the position on the screen that is recognized as a "response" in the saccadic response condition
         - Correct answers (integer), correct keys, incorrect answers, incorrect keys per trial
         - Positions of flashing circles
         - Evidence stream per flashing circle per trial
         - Opacity-per-frame for all flashing circles for all trials.
         """

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
        n_increments = np.ceil(self.stim_max_time * self.frame_rate / increment_length).astype(int)
        n_increments += 1  # 1 extra, in case we're dropping frames

        # Knowing this, we can define an index mask to select all frames that correspond to the between-increment
        # pause period
        mask_idx = np.tile(np.hstack((np.repeat([0], repeats=flash_length),
                                      np.repeat([1], repeats=pause_length))),
                           n_increments).astype(bool)

        # Define which flashing circle is correct in all n_trials
        self.correct_answers = self.design['correct_answer'].values.astype(int)
        # if self.correct_answers is None:
        #     raise(ValueError('Correct answers not yet set upon calling prepare_trials(). Is the design loaded?'))
        self.incorrect_answers = [np.delete(np.arange(self.n_flashers), i) for i in self.correct_answers if i in
                                  np.arange(self.n_flashers)]

        # # Which responses (keys or saccades) correspond to these flashers?
        # self.correct_responses = np.array(self.response_keys)[self.correct_answers]
        # self.incorrect_responses = [self.response_keys[self.incorrect_answers[i]] for i in range(n_trials)]

        # Initialize 'increment arrays' for correct and incorrect. These are arrays filled with 0s and 1s, determining
        # for each 'increment' whether a piece of evidence is shown or not.
        # (this is a bit loopy, but I can't be bothered to make nice matrices here)
        self.trial_arrays = []
        for trial_n in range(self.n_trials):

            # If the current trial is a null trial, or is a localizer trial, don't make an evidence array
            if self.design.iloc[trial_n]['null_trial'] or self.design.iloc[trial_n]['block_type'] == 'localizer':
                self.trial_arrays.append([[] * self.n_flashers])
                continue

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

    def run_null_trial(self, trial, phases):
        """ Runs a single null trial """

        NullTrial(ID=trial.trial_ID,
                  block_trial_ID=trial.block_trial_ID,
                  parameters={},
                  phase_durations=phases,
                  session=self,
                  screen=self.screen,
                  tracker=self.tracker).run()

    def run_localizer_trial(self, trial, phases):
        """ Runs a single localizer trial """

        if trial.response_modality == 'hand':
            trial_pointer = LocalizerTrialKeyboard
        elif trial.response_modality == 'eye':
            trial_pointer = LocalizerTrialSaccade
        else:
            raise (ValueError('The trial response type is not understood. %s was provided, but ''eye'' or '
                                          'hand'' is expected. Trial n: %d, block n: %d' % (trial.response_modality,
                                                                                            trial.trial_ID,
                                                                                            trial.block_num)))
        trial_object = trial_pointer(ID=trial.trial_ID,
                                     block_trial_ID=trial.block_trial_ID,
                                     parameters={'correct_answer': trial.correct_answer,
                                                 'cue': trial.cue,
                                                 'trial_type': trial.trial_type},
                                     phase_durations=phases,
                                     session=self,
                                     screen=self.screen,
                                     tracker=self.tracker)
        trial_object.run()

        return trial_object

    def run_experimental_trial(self, trial, phases, block_n):
        """ Runs a single experimental trial """

        # shortcut
        this_trial_type = trial.trial_type

        if trial.response_modality == 'hand':
            trial_pointer = FlashTrialKeyboard
        elif trial.response_modality == 'eye':
            trial_pointer = FlashTrialSaccade
        else:
            raise(ValueError('The trial response type is not understood. %s was provided, but ''eye'' or '
                             'hand'' is expected. Trial n: %d, block n: %d' % (trial.response_modality,
                                                                               trial.trial_ID,
                                                                               trial.block_num)))

        # In a limbic trial, prepare / update feedback
        if 'limbic' in trial.block_type:
            if this_trial_type in [0, 1]:  # Neutral condition
                self.feedback_text_objects[1].text = 'Correct!'
            elif this_trial_type in [2, 5]:  # Compatible cue condition
                self.feedback_text_objects[1].text = 'Correct! +8\nTotal score: %d' % (
                    self.participant_scores[block_n] + 8)
            elif this_trial_type in [3, 4]:  # Incompatible cue condition
                self.feedback_text_objects[1].text = 'Correct! +2\nTotal score: %d' % (
                    self.participant_scores[block_n] + 2)

        trial_object = trial_pointer(ID=trial.trial_ID,
                                     block_trial_ID=trial.block_trial_ID,
                                     parameters={'trial_evidence_arrays': self.trial_arrays[trial.trial_ID],
                                                 'correct_answer': trial.correct_answer.astype(int),
                                                 'cue': trial.cue,
                                                 'trial_type': trial.trial_type},
                                     phase_durations=phases,
                                     session=self,
                                     screen=self.screen,
                                     tracker=self.tracker)
        trial_object.run()

        # If the response given is correct, update scores
        if 'limbic' in trial.block_type and trial_object.response_type == 1:
            if this_trial_type in [2, 5]:
                self.participant_scores[block_n] += 8
            elif this_trial_type in [3, 4]:
                self.participant_scores[block_n] += 2

        return trial_object

    def run(self):
        """ Run the trials that were prepared. The experimental design must be loaded. """

        # Initialize variable to keep track of the number of instruction screens shown
        # Instruction screen IDs are negative. The first shown is -1, the second -2, etc.
        n_instruction_screens_shown = -1

        # Show DEBUG screen first, if we're in debug mode.
        if self.subject_initials == 'DEBUG':
            self.current_instruction = self.debug_screen
            FlashInstructions(ID=-99, parameters={}, phase_durations=[100],
                              session=self,
                              screen=self.screen,
                              tracker=self.tracker).run()

        # Show welcome screen
        self.current_instruction = self.welcome_screen
        FlashInstructions(ID=n_instruction_screens_shown, parameters={}, phase_durations=self.instructions_durations,
                          session=self,
                          screen=self.screen,
                          tracker=self.tracker).run()
        n_instruction_screens_shown -= 1  # Update instruction screen counter

        # Loop through blocks
        for block_n in range(5):

            # Get current block type, in order to find the corresponding instruction screens to show
            block_type = self.design.loc[self.design['block'] == block_n, 'block_type'].values[0]

            if block_type == 'cognitive_hand':
                self.instructions_to_show = self.cognitive_hand_instructions
            elif block_type == 'cognitive_eye':
                self.instructions_to_show = self.cognitive_eye_instructions
            elif block_type == 'limbic_hand':
                self.instructions_to_show = self.limbic_hand_instructions
            elif block_type == 'limbic_eye':
                self.instructions_to_show = self.limbic_eye_instructions
            elif block_type == 'localizer':
                self.instructions_to_show = self.localizer_instructions

            # Loop through instruction screens
            for instruction_screen_n in range(len(self.instructions_to_show)):

                # Set the current instruction correctly
                self.current_instruction = self.instructions_to_show[instruction_screen_n]

                # And "play"
                FlashInstructions(ID=n_instruction_screens_shown, parameters={},
                                  phase_durations=self.instructions_durations,
                                  session=self, screen=self.screen, tracker=self.tracker).run()
                n_instruction_screens_shown -= 1  # Update instruction screen counter

                # Check for stop signal during instruction screen
                if self.stopped:
                    self.close()

            # After instructions, set participant score for this block to 0
            self.participant_scores.append(0)

            # Get the trial handler of the current block
            trial_handler = self.trial_handlers[block_n]

            # Reset any changed feedback object text (SAT after limbic might otherwise show weird feedback)
            self.feedback_text_objects[1].text = 'Correct!'

            # Loop over block trials
            for trial in trial_handler:

                # shortcut (needed in all trial types)
                this_phases = (trial.phase_0,  # time to wait for scanner
                               trial.phase_1,  # pre-cue fixation cross
                               trial.phase_2,  # cue
                               trial.phase_3,  # post-cue fixation cross [0 for localizer]
                               trial.phase_4,  # stimulus
                               trial.phase_5,  # post-stimulus time (after response, before feedback)
                               trial.phase_6)  # feedback time

                # What trial type to run?
                if trial.null_trial:  # True or false
                    self.run_null_trial(trial, phases=this_phases)
                else:
                    if block_n == 0:   # Localizer
                        trial_object = self.run_localizer_trial(trial, phases=this_phases)
                    else:              # Experiment
                        trial_object = self.run_experimental_trial(trial, phases=this_phases, block_n=block_n)

                        # Save evidence arrays (only in experimental trials)
                        for flasher in range(self.n_flashers):
                            trial_handler.addData('evidence stream ' + str(flasher),
                                                  self.trial_arrays[trial.trial_ID][flasher][self.first_frame_idx])
                        trial_handler.addData('evidence shown at rt',
                                              trial_object.evidence_shown / self.standard_parameters['flash_length'])

                    # Save all data (only in non-null trials)
                    trial_handler.addData('rt', trial_object.response_time)
                    trial_handler.addData('response', trial_object.response)
                    trial_handler.addData('correct', trial_object.response_type == 1)
                    trial_handler.addData('feedback', self.feedback_text_objects[trial_object.response_type].text)

                # Trial finished, so on to the next entry
                self.exp_handler.nextEntry()

                # Check for stop flag in inner/trial loop
                if self.stopped:
                    break



                        # else:
                #     # Get trial type: LocalizerTrial or FlashTrial; plus, what kind of response should we expect?
                #     if block_n == 0:  # First block is always the localizer
                #         # LocalizerTrial, but what subclass?
                #         if this_response_modality == 'hand':
                #             trial_pointer = LocalizerTrialKeyboard
                #         elif this_response_modality == 'eye':
                #             trial_pointer = LocalizerTrialSaccade
                #         else:
                #             raise (ValueError('The trial response type is not understood. %s was provided, but ''eye'' or '
                #                               'hand'' is expected. Trial n: %d, block n: %d' % (this_response_modality,
                #                                                                                 this_ID,
                #                                                                                 block_n)))
                #     else:
                #         # FlashTrial, but what subclass?
                #         if this_response_modality == 'hand':
                #             trial_pointer = FlashTrialKeyboard
                #         elif this_response_modality == 'eye':
                #             trial_pointer = FlashTrialSaccade
                #         else:
                #             raise(ValueError('The trial response type is not understood. %s was provided, but ''eye'' or '
                #                              'hand'' is expected. Trial n: %d, block n: %d' % (this_response_modality,
                #                                                                                this_ID,
                #                                                                                block_n)))

                    # # In case the current block is a limbic block, make sure feedback is prepared properly
                    # if 'limbic' in trial.block_type:
                    #     if this_trial_type in [0, 1]:  # Neutral condition
                    #         self.feedback_text_objects[1].text = 'Correct!'
                    #     elif this_trial_type in [2, 5]:  # Compatible cue condition
                    #         self.feedback_text_objects[1].text = 'Correct! +8\nTotal score: %d' % (
                    #             self.participant_scores[block_n] + 8)
                    #     elif this_trial_type in [3, 4]:  # Incompatible cue condition
                    #         self.feedback_text_objects[1].text = 'Correct! +2\nTotal score: %d' % (
                    #             self.participant_scores[block_n] + 2)
                    #
                    # # Initialize and run trial
                    # # Note that we're always passing trial_evidence_arrays, even if we're in a localizer block. This is a
                    # #  bit ugly but allows us to use exactly the same method call here.
                    # trial_obj = trial_pointer(ID=this_ID,
                    #                           block_trial_ID=this_block_trial_ID,
                    #                           parameters={'trial_evidence_arrays': this_trial_evidence_array,
                    #                                       'correct_answer': this_correct_answer,
                    #                                       'cue': this_cue,
                    #                                       'trial_type': this_trial_type},
                    #                           phase_durations=this_phases,
                    #                           session=self,
                    #                           screen=self.screen,
                    #                           tracker=self.tracker)
                    # trial_obj.run()
                    #
                    # # If the response given is correct, update scores
                    # if 'limbic' in trial.block_type and trial_obj.response_type == 1:
                    #     if this_trial_type in [2, 5]:
                    #         self.participant_scores[block_n] += 8
                    #     elif this_trial_type in [3, 4]:
                    #         self.participant_scores[block_n] += 2

                    # # Save all data
                    # trial_handler.addData('rt', trial_obj.response_time)
                    # trial_handler.addData('response', trial_obj.response)
                    # trial_handler.addData('correct', trial_obj.response_type == 1)
                    # trial_handler.addData('feedback', self.feedback_text_objects[trial_obj.response_type].text)

                    # # For non-localizer blocks, also save the evidence arrays
                    # if block_n > 0:
                    #     for flasher in range(self.n_flashers):
                    #         trial_handler.addData('evidence stream ' + str(flasher),
                    #                               this_trial_evidence_array[flasher][self.first_frame_idx])
                    #     trial_handler.addData('evidence shown at rt',
                    #                           trial_obj.evidence_shown / self.standard_parameters['flash_length'])

                # # Trial finished, so on to the next entry
                # self.exp_handler.nextEntry()
                #
                # # Check for stop flag in inner/trial loop
                # if self.stopped:
                #     break

            # Check for stop flag in outer/block loop
            if self.stopped:
                break

        self.close()

    def close(self):
        """ Saves stuff and closes """
        self.exp_handler.saveAsPickle(self.exp_handler.dataFileName)
        self.exp_handler.saveAsWideText(self.exp_handler.dataFileName + '.csv')

        if self.screen.recordFrameIntervals:
            # Save frame intervals to file
            self.screen.saveFrameIntervals(fileName=self.output_file + '_frame_intervals.log', clear=False)

            # Make a nice figure
            intervals_ms = pylab.array(self.screen.frameIntervals) * 1000
            m = pylab.mean(intervals_ms)
            sd = pylab.std(intervals_ms)

            msg = "Mean=%.1fms, s.d.=%.2f, 99%%CI(frame)=%.2f-%.2f"
            dist_string = msg % (m, sd, m - 2.58 * sd, m + 2.58 * sd)
            n_total = len(intervals_ms)
            n_dropped = sum(intervals_ms > (1.5 * m))
            msg = "Dropped/Frames = %i/%i = %.3f%%"
            dropped_string = msg % (n_dropped, n_total, 100 * n_dropped / float(n_total))

            # plot the frame intervals
            pylab.figure(figsize=[12, 8])
            pylab.subplot(1, 2, 1)
            pylab.plot(intervals_ms, '-')
            pylab.ylabel('t (ms)')
            pylab.xlabel('frame N')
            pylab.title(dropped_string)

            pylab.subplot(1, 2, 2)
            pylab.hist(intervals_ms, 50, normed=0, histtype='stepfilled')
            pylab.xlabel('t (ms)')
            pylab.ylabel('n frames')
            pylab.title(dist_string)
            pylab.savefig(self.output_file + '_frame_intervals.png')

        super(FlashSession, self).close()

#
# class FlashSessionPayoffBias(FlashSession):
#     """
#     Subclasses FlashSession to handle an experimental session to a 3 x 2 (cue x correct) asymmetric pay-off bias design.
#
#     Each trial has 6 phases:
#     0. Fixation cross until scanner pulse
#     1. Show cue (0.5s)
#     2. Fixation cross (0.5s; this should be jittered)
#     3. Stimulus presentation; participant can respond
#     4. Stimulus presentation after participant has responded (until 1.5s has passed since phase 2)
#     5. Feedback (0.5s)
#     6. ITI (1s; this should be jittered)
#
#     The cue is either 'NEU', 'LEFT', or 'RIGHT'. If the cue was NEU, any response (correct or incorrect) gets a
#     pay-off of 0. If the cue was congruent with the correct answer, the participant receives 8 points for a correct
#     answer. If the cue is incongruent with the correct answer, the participant receives 2 points for a correct
#     answer. No points for too fast (<150ms), too late (>1.5s), or wrong answers.
#     """
#
#     def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
#         super(FlashSessionPayoffBias, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system)
#
#         self.trial_types = None
#         self.cue_by_trial = None
#         self.prepare_trials()
#         self.participant_score = 0
#
#     def prepare_trials(self):
#         """
#         Trial conditions are set up as follows:
#         0. Neutral cue, left is correct. Pay-off: 0
#         1. Neutral cue, right is correct. Pay-off: 0
#         2. Left cue, left is correct. Pay-off: 8 if correct (0 if incorrect)
#         3. Left cue, right is correct. Pay-off: 2 if correct (0 if incorrect)
#         4. Right cue, left is correct. Pay-off: 2 if correct (0 if incorrect)
#         5. Right cue, right is correct. Pay-off: 8 if correct (0 if incorrect)
#         """
#
#         self.trial_types = np.hstack((np.repeat([0, 1], repeats=n_trials/6),    # Neutral cue, left/right corr
#                                       np.repeat([2, 3], repeats=n_trials/6),    # Left cue, left/right corr
#                                       np.repeat([4, 5], repeats=n_trials/6)))   # Right cue, left/right corr
#         np.random.shuffle(self.trial_types)
#
#         if self.trial_types.shape[0] != n_trials:
#             raise(ValueError('The provided n_trials (%d) could not be split into the correct number of trial types. '
#                              'Closest option is %d trials' % (n_trials, self.trial_types.shape[0])))
#
#         self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
#         self.correct_answers = np.zeros(n_trials, dtype=np.int8)
#
#         self.cue_by_trial[(self.trial_types == 0) | (self.trial_types == 1)] = 'NEU'
#         self.cue_by_trial[(self.trial_types == 2) | (self.trial_types == 3)] = 'LEFT'
#         self.cue_by_trial[(self.trial_types == 4) | (self.trial_types == 5)] = 'RIGHT'
#
#         self.correct_answers[(self.trial_types == 0) |
#                              (self.trial_types == 2) |
#                              (self.trial_types == 4)] = 0  # 0 = left is correct
#         self.correct_answers[(self.trial_types == 1) |
#                              (self.trial_types == 3) |
#                              (self.trial_types == 5)] = 1  # 1 = right is correct
#
#         # Exported trial types to check whether everything went ok
#         trial_data = pd.DataFrame({'ID': np.arange(n_trials),
#                                    'correct_answer': self.correct_answers,
#                                    'cue': self.cue_by_trial,
#                                    'trial_types': self.trial_types})
#         trial_data.to_csv(self.output_file + '_trial_types.csv', index=False)
#
#         # Set-up trial handler
#         self.trial_handler = data.TrialHandler(trial_data.to_dict('records'), 1, extraInfo=
#                                                {'subject_initials': self.subject_initials,
#                                                 'index_number': self.index_number,
#                                                 'session_type': session_type,
#                                                 }, method='sequential')
#         self.exp_handler.addLoop(self.trial_handler)
#
#         super(FlashSessionPayoffBias, self).prepare_trials()
#
#     def run(self):
#         # Show instruction first
#         FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
#                           tracker=self.tracker).run()
#
#         # Loop through trials
#         for this_trial in self.trial_handler:
#             this_ID = this_trial['ID']
#             this_trial_type = this_trial['trial_type']
#             this_cue = this_trial['cue']
#             this_correct_answer = this_trial['correct_answer']
#             this_trial_evidence_array = self.trial_arrays[this_ID]
#
#             # Prepare feedback, in case the participant responds correctly
#             if this_trial_type in [0, 1]:           # Neutral condition
#                 self.feedback_text_objects[1].text = 'Correct!'
#             elif this_trial_type in [2, 5]:         # Compatible cue condition
#                 self.feedback_text_objects[1].text = 'Correct! +8\nTotal score: %d' % (self.participant_score+8)
#             elif this_trial_type in [3, 4]:         # Incompatible cue condition
#                 self.feedback_text_objects[1].text = 'Correct! +2\nTotal score: %d' % (self.participant_score+2)
#
#             trial = self.trial_pointer(ID=this_ID,
#                                        parameters={'trial_evidence_arrays': this_trial_evidence_array,
#                                                    'correct_answer': this_correct_answer,
#                                                    'cue': this_cue,
#                                                    'trial_type': this_trial_type},
#                                        phase_durations=phase_durations,
#                                        session=self,
#                                        screen=self.screen,
#                                        tracker=self.tracker)
#
#             trial.run()
#
#             # If the response given is correct, update scores
#             if trial.response_type == 1:
#                 if this_trial_type in [2, 5]:
#                     self.participant_score += 8
#                 elif this_trial_type in [3, 4]:
#                     self.participant_score += 2
#
#             # Add all data
#             self.trial_handler.addData('rt', trial.response_time)
#             self.trial_handler.addData('response', trial.response)
#             self.trial_handler.addData('correct', trial.response_type == 1)
#             for flasher in range(self.n_flashers):
#                 self.trial_handler.addData('evidence stream ' + str(flasher),
#                                            this_trial_evidence_array[flasher][self.first_frame_idx])
#
#             self.trial_handler.addData('evidence shown at rt',
#                                        trial.evidence_shown/self.standard_parameters['flash_length'])
#             self.exp_handler.nextEntry()
#
#             if self.stopped:
#                 break
#
#         self.close()
#
#
# class FlashSessionSAT(FlashSession):
#     """
#     Subclasses FlashSession to handle an experimental session to a 2 x 2 (cue x correct) speed-accuracy trade-off
#     design.
#
#     Each trial has 6 phases:
#     0. Fixation cross until scanner pulse
#     1. Show cue (0.5s)
#     2. Fixation cross (0.5s; this should be jittered)
#     3. Stimulus presentation; participant can respond
#     4. Stimulus presentation after participant has responded (until 1.5s has passed since phase 2)
#     5. Feedback (0.5s)
#     6. ITI (1s; this should be jittered)
#
#     The cue is either 'SP', or 'ACC'.
#     """
#
#     def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
#         super(FlashSessionSAT, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system)
#
#         self.trial_types = None
#         self.cue_by_trial = None
#         self.prepare_trials()
#
#     def prepare_trials(self):
#         """
#         """
#
#         self.trial_types = np.hstack(
#             (np.repeat([0, 1], repeats=n_trials / 4),   # SPEED cue, left/right corr
#              np.repeat([2, 3], repeats=n_trials / 4)))  # ACCURACY cue, left/right corr
#
#         np.random.shuffle(self.trial_types)
#
#         if self.trial_types.shape[0] != n_trials:
#             raise(ValueError('The provided n_trials (%d) could not be split into the correct number of trial types. '
#                              'Closest option is %d trials' % (n_trials, self.trial_types.shape[0])))
#
#         self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
#         self.correct_answers = np.zeros(n_trials, dtype=np.int8)
#
#         self.cue_by_trial[(self.trial_types == 0) | (self.trial_types == 1)] = 'SP'
#         self.cue_by_trial[(self.trial_types == 2) | (self.trial_types == 3)] = 'ACC'
#
#         self.correct_answers[(self.trial_types == 0) |
#                              (self.trial_types == 2)] = 0  # 0 = left is correct
#         self.correct_answers[(self.trial_types == 1) |
#                              (self.trial_types == 3)] = 1  # 1 = right is correct
#
#         # Exported trial types to check whether everything went ok
#         trial_data = pd.DataFrame({'ID': np.arange(n_trials),
#                                    'correct_answer': self.correct_answers,
#                                    'cue': self.cue_by_trial,
#                                    'trial_type': self.trial_types})
#         trial_data.to_csv(self.output_file + '_trial_types.csv', index=False)
#
#         # Set-up trial handler
#         self.trial_handler = data.TrialHandler(trial_data.to_dict('records'), 1,
#                                                extraInfo={'subject_initials': self.subject_initials,
#                                                           'index_number': self.index_number,
#                                                           'session_type': session_type,
#                                                           },
#                                                method='sequential')
#         self.exp_handler.addLoop(self.trial_handler)
#
#         super(FlashSessionSAT, self).prepare_trials()
#
#     def run(self):
#         # Show instruction first
#         FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
#                           tracker=self.tracker).run()
#
#         # Loop through trials
#         for this_trial in self.trial_handler:
#             this_ID = this_trial['ID']
#             this_trial_type = this_trial['trial_type']
#             this_cue = this_trial['cue']
#             this_correct_answer = this_trial['correct_answer']
#             this_trial_evidence_array = self.trial_arrays[this_ID]
#
#             trial = self.trial_pointer(ID=this_ID,
#                                        parameters={'trial_evidence_arrays': this_trial_evidence_array,
#                                                    'correct_answer': this_correct_answer,
#                                                    'cue': this_cue,
#                                                    'trial_type': this_trial_type},
#                                        phase_durations=phase_durations,
#                                        session=self,
#                                        screen=self.screen,
#                                        tracker=self.tracker)
#             trial.run()
#
#             # Add all data
#             self.trial_handler.addData('rt', trial.response_time)
#             self.trial_handler.addData('response', trial.response)
#             self.trial_handler.addData('correct', trial.response_type == 1)
#
#             for flasher in range(self.n_flashers):
#                 self.trial_handler.addData('evidence stream ' + str(flasher),
#                                            this_trial_evidence_array[flasher][self.first_frame_idx])
#             self.trial_handler.addData('evidence shown at rt',
#                                        trial.evidence_shown/self.standard_parameters['flash_length'])
#
#             self.exp_handler.nextEntry()
#
#             if self.stopped:
#                 break
#
#         self.close()
#
#
# class FlashSessionMotor(FlashSession):
#     """
#     Subclasses FlashSession to handle an experimental session to a 2 x 2 (cue x correct) speed-accuracy trade-off
#     design.
#
#     Each trial has 6 phases:
#     0. Fixation cross until scanner pulse
#     1. Show cue (0.5s)
#     2. Fixation cross (0.5s; this should be jittered)
#     3. Stimulus presentation; participant can respond
#     4. Stimulus presentation after participant has responded (until 1.5s has passed since phase 2)
#     5. Feedback (0.5s)
#     6. ITI (1s; this should be jittered)
#
#     The cue is either 'eye', or 'hand'.
#     """
#
#     def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False):
#         super(FlashSessionMotor, self).__init__(subject_initials, index_number, scanner, tracker_on, sound_system)
#
#         # These are not set correctly for this manipulation
#         self.response_keys = np.array(response_keys)
#         self.eye_travel_threshold = 3
#         self.trial_pointer = None
#
#         self.trial_types = None
#         self.cue_by_trial = None
#         self.prepare_trials()
#
#     def prepare_trials(self):
#         """
#         """
#
#         self.trial_types = np.hstack(
#             (np.repeat([0, 1], repeats=n_trials / 4),   # EYE cue, left/right corr
#              np.repeat([2, 3], repeats=n_trials / 4)))  # HAND cue, left/right corr
#
#         np.random.shuffle(self.trial_types)
#
#         if self.trial_types.shape[0] != n_trials:
#             raise (
#                 ValueError(
#                     'The provided n_trials (%d) could not be split into the correct number of trial types. '
#                     'Closest option is %d trials' % (n_trials, self.trial_types.shape[0])))
#
#         self.cue_by_trial = np.zeros(n_trials, dtype='<U5')
#         self.correct_answers = np.zeros(n_trials, dtype=np.int8)
#
#         self.cue_by_trial[(self.trial_types == 0) | (self.trial_types == 1)] = 'EYE'
#         self.cue_by_trial[(self.trial_types == 2) | (self.trial_types == 3)] = 'HAND'
#
#         self.correct_answers[(self.trial_types == 0) |
#                              (self.trial_types == 2)] = 0  # 0 = left is correct
#         self.correct_answers[(self.trial_types == 1) |
#                              (self.trial_types == 3)] = 1  # 1 = right is correct
#
#         # Exported trial types to check whether everything went ok
#         trial_data = pd.DataFrame({'ID': np.arange(n_trials),
#                                    'correct_answer': self.correct_answers,
#                                    'cue': self.cue_by_trial,
#                                    'trial_type': self.trial_types})
#         trial_data.to_csv(self.output_file + '_trial_types.csv', index=False)
#
#         # Set-up trial handler
#         self.trial_handler = data.TrialHandler(trial_data.to_dict('records'), 1,
#                                                extraInfo={'subject_initials': self.subject_initials,
#                                                           'index_number': self.index_number,
#                                                           'session_type': session_type,
#                                                           },
#                                                method='sequential')
#         self.exp_handler.addLoop(self.trial_handler)
#
#         super(FlashSessionMotor, self).prepare_trials()
#
#     def run(self):
#         # Show instruction first
#         FlashInstructions(ID=-1, parameters={}, phase_durations=[100], session=self, screen=self.screen,
#                           tracker=self.tracker).run()
#
#         # Loop through trials
#         for this_trial in self.trial_handler:
#             this_ID = this_trial['ID']
#             this_trial_type = this_trial['trial_type']
#             this_cue = this_trial['cue']
#             this_correct_answer = this_trial['correct_answer']
#             this_trial_evidence_array = self.trial_arrays[this_ID]
#
#             if this_cue == 'EYE':
#                 trial_pointer = FlashTrialSaccade
#             elif this_cue == 'HAND':
#                 trial_pointer = FlashTrialKeyboard
#             else:
#                 raise(ValueError('Something is wrong: cue type not understood; should be EYE or HAND'))
#
#             trial = trial_pointer(ID=this_ID,
#                                   parameters={'trial_evidence_arrays': this_trial_evidence_array,
#                                               'correct_answer': this_correct_answer,
#                                               'cue': this_cue,
#                                               'trial_type': this_trial_type},
#                                   phase_durations=phase_durations,
#                                   session=self,
#                                   screen=self.screen,
#                                   tracker=self.tracker)
#             trial.run()
#
#             # Add all data
#             self.trial_handler.addData('rt', trial.response_time)
#             self.trial_handler.addData('response', trial.response)
#             self.trial_handler.addData('correct', trial.response_type == 1)
#
#             for flasher in range(self.n_flashers):
#                 self.trial_handler.addData('evidence stream ' + str(flasher),
#                                            this_trial_evidence_array[flasher][self.first_frame_idx])
#
#             self.trial_handler.addData('evidence shown at rt',
#                                        trial.evidence_shown/self.standard_parameters['flash_length'])
#
#             self.exp_handler.nextEntry()
#
#             if self.stopped:
#                 break
#
#         self.close()

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
