#!/usr/bin/env python
# encoding: utf-8
from __future__ import division
from exp_tools import EyelinkSession
from psychopy import monitors, data, info, logging
from standard_parameters import *
from warnings import warn
import pylab
import pandas as pd
import os
import sys
from glob import glob
import cPickle as pickle

from FlashTrial import *
from FlashInstructions import *
from FlashStim import FlashStim
from LocalizerTrial import *
from NullTrial import *
from FixationCross import *

import pylink

class FlashSession(EyelinkSession):
    """
    Session of the "Flashing Circles" task with eye-tracking enabled.

    In this task, the participant is shown two flashing circles. Each circle has a predetermined probability of
    flashing at every time point. The task is to decide which circle flashes most often.

    Participants can either respond via keyboard or with a saccade.

    Parameters
    -----------
    subject_initials: str
    index_number: int
    scanner: str
        'n' for no scanner, anything else for a scanner. ToDo: change to bool?
    tracker_on: bool
        If True, attempts to connect to eye-link tracker. If no connection is found, creates a dummy tracker (mouse)
        If False, doesn't create anything.
        Should be True for the experiment, possibly also for practice
    sound_system: bool
        Should the sound system be initialized? Note that I got an error on my laptop with True, so not sure if this
        works
    language: str {'en', 'nl'}
        What language should we show instructions and feedback?
    mirror: bool
        Horizontally flip everything? UNTESTED, AND NOT NECESSARY. Built-in for a session at the mock scanner,
        which will no longer be used.
    start_block: int [0-5]
        With which block should we start? 0 = Localizer, 1-4 are experimental blocks
    start_score: int
        With what participant score should we start? Usually 0, but if the session is restarted in a later block,
        might be some number.
    """

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False, language='en',
                 mirror=False, start_block=0, start_score=0):
        super(FlashSession, self).__init__(subject_initials, index_number, sound_system)

        # Set-up screen
        screen = self.create_screen(size=screen_res, full_screen=1, physical_screen_distance=159.0,
                                    background_color=background_color, physical_screen_size=(70, 40),
                                    monitor=monitor_name)
        self.screen.monitor = monitors.Monitor(monitor_name)
        self.screen.recordFrameIntervals = record_intervals
        self.mouse = event.Mouse(win=screen, visible=False)

        # For logging: set-up output file name, experiment handler
        self.create_output_file_name(data_directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))

        # save a log file for detail verbose info
        logFile = logging.LogFile(self.output_file + '.log', level=logging.EXP)

        self.trial_handlers = []
        self.participant_score = start_score
        self.n_instructions_shown = -1
        self.start_block = start_block

        # TR of MRI
        self.TR = TR

        # If we're running in debug mode, only show the instruction screens for 1 sec each.
        if self.subject_initials == 'DEBUG':
            self.instructions_durations = [1]
        else:
            # Otherwise show them for maximum 30 minutes (the user should skip screens).
            self.instructions_durations = [1800]

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

        # Ensure that relative paths start from the same directory as this script
        _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
        self.exp_handler = data.ExperimentHandler(name='flashtask',
                                                  version='0.9.0',
                                                  extraInfo={'subject_initials': subject_initials,
                                                             'index_number': index_number,
                                                             'scanner': scanner,
                                                             'tracker_on': tracker_on,
                                                             'frame_rate': self.screen.getActualFrameRate(),
                                                             'eyelink_tmp_file_name': self.eyelink_temp_file,
                                                             'language': language,
                                                             'n_flashers': parameters['n_flashers'],
                                                             'radius flashers': parameters[
                                                                 'radius_deg'],
                                                             'flasher size': parameters['flasher_size']},
                                                  runtimeInfo=info.RunTimeInfo,
                                                  dataFileName=os.path.join(_thisDir, self.output_file),
                                                  autoLog=True)

        self.scanner = scanner  # either 'n' for no scanner, or 'y' for scanner.
        self.standard_parameters = parameters
        self.sat_feedback_parameters = sat

        # Initialize a bunch of attributes used in load_design() or prepare_trials()
        self.mirror = mirror
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
        self.last_ID_this_block = None

        # Get session information about flashers
        self.n_flashers = self.standard_parameters['n_flashers']
        self.radius_deg = self.standard_parameters['radius_deg']
        self.flasher_size = self.standard_parameters['flasher_size']

        # Initialize psychopy.visual objects attributes and language
        self.language = language
        self.feedback_text_objects = None
        self.fixation_cross = None
        self.stimulus = None
        self.cue_object = None
        self.arrow_stimuli = None
        self.scanner_wait_screen = None
        self.localizer_instructions_eye = None
        self.localizer_instructions_hand = None
        self.cognitive_eye_instructions = None
        self.cognitive_hand_instructions = None
        self.limbic_eye_instructions = None
        self.limbic_hand_instructions = None
        self.welcome_screen = None
        self.current_instruction = None
        self.feedback_txt = None
        self.instructions_to_show = None

        self.response_keys = np.array(response_keys)

        # Radius for eye movement detection: 1.5 degrees?
        self.eye_travel_threshold = 1.5

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

        Note that instruction texts are read from .txt-files in the package.
        """

        # Load all instruction texts
        this_file = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(this_file, 'instructions', self.language, 'feedback.txt'), 'rb') as f:
            self.feedback_txt = f.read().split('\n\n\n')

        with open(os.path.join(this_file, 'instructions', self.language, 'scanner_wait.txt'), 'rb') as f:
            scanner_wait_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'welcome_exp.txt'), 'rb') as f:
            welcome_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'localizer_eye.txt'), 'rb') as f:
            localizer_eye_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'localizer_eye_start.txt'), 'rb') as f:
            localizer_eye_start_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'localizer_hand.txt'), 'rb') as f:
            localizer_hand_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'localizer_hand_start.txt'), 'rb') as f:
            localizer_hand_start_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'cognitive_eye.txt'), 'rb') as f:
            cognitive_eye_txt = f.read().split('\n\n\n')

        with open(os.path.join(this_file, 'instructions', self.language, 'cognitive_hand.txt'), 'rb') as f:
            cognitive_hand_txt = f.read().split('\n\n\n')

        with open(os.path.join(this_file, 'instructions', self.language, 'limbic_eye.txt'), 'rb') as f:
            limbic_eye_txt = f.read().split('\n\n\n')

        with open(os.path.join(this_file, 'instructions', self.language, 'limbic_hand.txt'), 'rb') as f:
            limbic_hand_txt = f.read().split('\n\n\n')

        # Prepare fixation cross
        self.fixation_cross = FixationCross(win=self.screen,
                                            inner_radius=fix_cross_parameters['inner_radius_degrees'],
                                            outer_radius=fix_cross_parameters['outer_radius_degrees'],
                                            bg=background_color)

        # Prepare cue
        self.cue_object = visual.TextStim(win=self.screen, text='Cue here', units='cm', height=visual_sizes[
            'cue_object'])

        # Prepare feedback stimuli
        self.feedback_text_objects = [
            # 0 = Too slow
            visual.TextStim(win=self.screen, text=self.feedback_txt[0], color='darkred', units='deg',
                            height=visual_sizes['fb_text'], flipHoriz=self.mirror),
            # 1 = correct
            visual.TextStim(win=self.screen, text=self.feedback_txt[1], color='darkgreen', units='deg',
                            height=visual_sizes['fb_text'], flipHoriz=self.mirror),
            # 2 = wrong
            visual.TextStim(win=self.screen, text=self.feedback_txt[2], color='darkred', units='deg',
                            height=visual_sizes['fb_text'], flipHoriz=self.mirror),
            # 3 = too fast
            visual.TextStim(win=self.screen, text=self.feedback_txt[3], color='darkred', units='deg',
                            height=visual_sizes['fb_text'], flipHoriz=self.mirror),
            # 4 = early phase
            visual.TextStim(win=self.screen, text=self.feedback_txt[4], color='darkred', units='deg',
                            height=visual_sizes['fb_text'], flipHoriz=self.mirror),
        ]

        self.block_end_instructions = [
            visual.TextStim(win=self.screen, text='End of block reached. Waiting for operator...\n\nPress R to '
                                                  'recalibrate, or space to proceed.',
                            name='end_block_instr',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=True, height=30, alignHoriz='center', units='pix',
                            )
        ]

        # Prepare localizer stimuli
        arrow_right_vertices = [(-0.2, 0.05),
                                (-0.2, -0.05),
                                (-.0, -0.05),
                                (0, -0.1),
                                (0.2, 0),
                                (0, 0.1),
                                (0, 0.05)]
        arrow_left_vertices = [(0.2, 0.05),
                               (0.2, -0.05),
                               (0.0, -0.05),
                               (0, -0.1),
                               (-0.2, 0),
                               (0, 0.1),
                               (0, 0.05)]

        if self.mirror:
            # Swap left & right
            arrow_right_vertices, arrow_left_vertices = arrow_left_vertices, arrow_right_vertices

        arrow_neutral_vertices = [(0.2, 0.0),  # Right point
                                  (0.1, 0.1),  # Towards up, left
                                  (0.1, 0.05),  # Down
                                  (-0.1, 0.05),  # Left
                                  (-0.1, 0.1),  # Up
                                  (-0.2, 0.0),  # Left point
                                  (-0.1, -0.1),  # Down, right
                                  (-0.1, -0.05),  # Up
                                  (0.1, -0.05),  # Right
                                  (0.1, -0.1)]  # Down

        self.arrow_stimuli = [
            visual.ShapeStim(win=self.screen, vertices=arrow_left_vertices, fillColor='lightgray',
                             size=visual_sizes['arrows'], lineColor='lightgray', units='deg'),
            visual.ShapeStim(win=self.screen, vertices=arrow_right_vertices, fillColor='lightgray',
                             size=visual_sizes['arrows'], lineColor='lightgray', units='deg'),
            visual.ShapeStim(win=self.screen, vertices=arrow_neutral_vertices, fillColor='lightgray',
                             size=visual_sizes['arrows'], lineColor='lightgray', units='deg')
        ]

        self.crosses = [
            visual.TextStim(win=self.screen, text='+', pos=(-10, 0), height=visual_sizes['crosses'], units='deg'),
            visual.TextStim(win=self.screen, text='+', pos=(10, 0), height=visual_sizes['crosses'], units='deg')
        ]

        # Prepare waiting for scanner-screen
        self.scanner_wait_screen = visual.TextStim(win=self.screen,
                                                   text=scanner_wait_txt,
                                                   name='scanner_wait_screen',
                                                   units='pix', font='Helvetica Neue', pos=(0, 0),
                                                   italic=True,
                                                   height=30, alignHoriz='center', flipHoriz=self.mirror)

        self.recalibration_error_screen = [
            visual.TextStim(win=self.screen,
                            text='Could not recalibrate: not connected to tracker...\n\nPress space to proceed with '
                                 'the experiment.',
                            name='recalibration_error_screen',
                            italic=True, height=30, color='darkred', alignHoriz='center', flipHoriz=self.mirror)
        ]

        # Keep debug screen at hand
        self.debug_screen = visual.TextStim(win=self.screen,
                                            text='DEBUG MODE. DO NOT RUN AN ACTUAL EXPERIMENT',
                                            name='debug_screen',
                                            color='darkred', height=1, units='cm', flipHoriz=self.mirror)

        # Prepare welcome screen
        self.welcome_screen = visual.TextStim(win=self.screen,
                                              text=welcome_txt,
                                              name='welcome_screen',
                                              units='pix', font='Helvetica Neue', pos=(0, 0),
                                              italic=False, height=30, alignHoriz='center', flipHoriz=self.mirror)

        # Prepare instruction screens
        self.localizer_instructions_eye = [
            visual.TextStim(win=self.screen,
                            text=localizer_eye_txt,
                            name='localizer_instructions_eye',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
        ]

        self.localizer_instructions_eye_start = [
            visual.TextStim(win=self.screen,
                            text=localizer_eye_start_txt,
                            name='localizer_instructions_eye_start',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
        ]

        self.localizer_instructions_hand_start = [
            visual.TextStim(win=self.screen,
                            text=localizer_hand_start_txt,
                            name='localizer_instructions_hand_start',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
        ]

        self.localizer_instructions_hand = [
            visual.TextStim(win=self.screen,
                            text=localizer_hand_txt,
                            name='localizer_instructions_hand',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
        ]

        self.cognitive_eye_instructions = [
            visual.TextStim(win=self.screen, text=cognitive_eye_txt[0],
                            font='Helvetica Neue', pos=(0, 0),
                            name='cognitive_eye_screen_1',
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=cognitive_eye_txt[1],
                            name='cognitive_eye_screen_2',
                            font='Helvetica Neue', pos=(0, 0), italic=False, height=30, alignHoriz='center',
                            units='pix', flipHoriz=self.mirror)
        ]

        self.cognitive_hand_instructions = [
            visual.TextStim(win=self.screen, text=cognitive_hand_txt[0],
                            font='Helvetica Neue', pos=(0, 0),
                            name='cognitive_hand_screen_1',
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=cognitive_hand_txt[1],
                            name='cognitive_hand_screen_2',
                            font='Helvetica Neue', pos=(0, 0), italic=False, height=30, alignHoriz='center',
                            units='pix', flipHoriz=self.mirror)
        ]

        self.limbic_eye_instructions = [
            visual.TextStim(win=self.screen, text=limbic_eye_txt[0],
                            font='Helvetica Neue', pos=(0, 0),
                            name='limbic_eye_screen_1',
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=limbic_eye_txt[1],
                            font='Helvetica Neue', pos=(0, 0),
                            name='limbic_eye_screen_2',
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=limbic_eye_txt[2],
                            name='limbic_eye_screen_3',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=limbic_eye_txt[3],
                            name='limbic_eye_screen_4',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror)
        ]

        self.limbic_hand_instructions = [
            visual.TextStim(win=self.screen, text=limbic_hand_txt[0],
                            font='Helvetica Neue', pos=(0, 0),
                            name='limbic_hand_screen_1',
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=limbic_hand_txt[1],
                            font='Helvetica Neue', pos=(0, 0),
                            name='limbic_hand_screen_2',
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=limbic_hand_txt[2],
                            name='limbic_hand_screen_3',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror),
            visual.TextStim(win=self.screen, text=limbic_hand_txt[3],
                            name='limbic_hand_screen_4',
                            font='Helvetica Neue', pos=(0, 0),
                            italic=False, height=30, alignHoriz='center', units='pix', flipHoriz=self.mirror)
        ]

    def prepare_trials(self):
        """
        Prepares everything necessary to make flashing circles trials:
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

        radius_cm = self.centimeters_per_degree * self.radius_deg
        pos_x = radius_cm * np.cos(t + np.arange(1, self.n_flashers+1) * 2 * np.pi / self.n_flashers)
        pos_y = radius_cm * np.sin(t + np.arange(1, self.n_flashers+1) * 2 * np.pi / self.n_flashers)

        # Flip the horizontal axis if there's a mirror
        if self.mirror:
            pos_x = -pos_x

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

        # Get the number of trials from the design; this is the the number of rows in the DataFrame.
        self.n_trials = self.design.shape[0]

        # Get the maximum duration a stimulus is shown
        self.stim_max_time = self.design.loc[self.design['block_type'] != 'localizer', 'phase_4'].max()

        # Make sure the correct_answers are extracted from the design
        self.correct_answers = self.design['correct_answer'].values.astype(int)

        # Define which flashing circle is correct in all n_trials
        self.incorrect_answers = [np.delete(np.arange(self.n_flashers), i) for i in self.correct_answers if i in
                                  np.arange(self.n_flashers)]

        # How many increments can we show during the stimulus period, with the specified increment_length and current
        # frame rate?
        n_increments = np.ceil(self.stim_max_time * self.frame_rate / increment_length).astype(int)
        n_increments += 1  # 1 full increment extra, in case we're dropping frames

        # Knowing this, we can define an index mask to select all frames that correspond to the between-increment
        # pause period
        mask_idx = np.tile(np.hstack((np.repeat([0], repeats=flash_length),
                                      np.repeat([1], repeats=pause_length))),
                           n_increments).astype(bool)

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
                self.trial_arrays.append(None)
                continue
            corr_answer_this_trial = self.correct_answers[trial_n]   # shortcut

            # Ensure that, at the end of the trial, there is more evidence for the correct choice alternative than for
            # any of the other choice alternatives
            good_evidence_streams = False
            while not good_evidence_streams:
                evidence_streams_this_trial = []
                total_evidence_per_flasher = []
                for i in range(self.n_flashers):

                    # First, create initial evidence stream
                    if i == corr_answer_this_trial:
                        evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_correct,
                                                                          size=n_increments).astype(np.int8)
                    else:
                        evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_incorrect,
                                                                          size=n_increments).astype(np.int8)

                    # How many pieces of evidence are shown in total for this flasher?
                    total_evidence_per_flasher.append(np.sum(evidence_stream_this_flasher))

                    # Repeat every increment for n_frames
                    evidence_stream_this_flasher = np.repeat(evidence_stream_this_flasher, increment_length)
                    evidence_stream_this_flasher[mask_idx] = 0   # add pause

                    evidence_streams_this_trial.append(evidence_stream_this_flasher)

                # Check if the evidence for the correct flasher is at least the evidence for each other flasher
                total_evidence_per_flasher = np.array(total_evidence_per_flasher)
                mask = np.ones(total_evidence_per_flasher.shape[0], np.bool)  # Create mask: compare correct to others
                mask[corr_answer_this_trial] = 0
                if (total_evidence_per_flasher[corr_answer_this_trial] >= total_evidence_per_flasher)[mask].all():
                    good_evidence_streams = True

            self.trial_arrays.append(evidence_streams_this_trial)

        # Create new mask to select only first frame of every increment
        self.first_frame_idx = np.arange(0, mask_idx.shape[0], increment_length)

    def run_null_trial(self, trial, phases, draw_crosses=False):
        """ Runs a single null trial """

        trial_object = NullTrial(ID=trial.trial_ID,
                                 block_trial_ID=trial.block_trial_ID,
                                 parameters={'draw_crosses': draw_crosses},
                                 phase_durations=phases,
                                 session=self,
                                 screen=self.screen,
                                 tracker=self.tracker)
        trial_object.run()

        return trial_object

    def run_localizer_trial(self, trial, phases):
        """ Runs a single localizer trial """

        if trial.response_modality == 'hand':
            trial_pointer = LocalizerTrialKeyboard
        elif trial.response_modality == 'eye':
            trial_pointer = LocalizerTrialSaccade
        else:
            raise (ValueError('The trial response type is not understood. %s was provided, but ''eye'' or '
                              'hand'' is expected. Trial n: %d, block n: 0' % (trial.response_modality,
                                                                               trial.trial_ID)))

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
                self.feedback_text_objects[1].text = self.feedback_txt[1]
            elif this_trial_type in [2, 5]:  # Compatible cue condition
                self.feedback_text_objects[1].text = self.feedback_txt[1] + ' +8\n' + self.feedback_txt[6] + ' %d' % (
                    self.participant_score + 8)
            elif this_trial_type in [3, 4]:  # Incompatible cue condition
                self.feedback_text_objects[1].text = self.feedback_txt[1] + ' +2\n' + self.feedback_txt[6] + ' %d' % (
                    self.participant_score + 2)

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
                self.participant_score += 8
            elif this_trial_type in [3, 4]:
                self.participant_score += 2

        return trial_object

    def show_instructions(self, trial_handler, end_block=False, phase_durations=None, respond_possible=True):
        """ Shows current instructions """

        if end_block:
            instr_obj = FlashEndBlockInstructions
            self.instructions_to_show = self.block_end_instructions
        else:
            instr_obj = FlashInstructions

        if phase_durations is None:
            phase_durations = self.instructions_durations

        if not respond_possible:
            instr_obj = FlashInstructionsNoResp
            phase_durations = [11.5]

        # Loop over self.current_instructions
        for instruction_n in range(len(self.instructions_to_show)):
            self.current_instruction = self.instructions_to_show[instruction_n]
            instr_trial = instr_obj(ID=self.n_instructions_shown,
                                    parameters={},
                                    phase_durations=phase_durations,
                                    session=self,
                                    screen=self.screen,
                                    tracker=self.tracker)
            instr_trial.run()

            trial_handler.addData('instr_screen_nr', self.n_instructions_shown)
            trial_handler.addData('instr_start_time', instr_trial.start_time)
            trial_handler.addData('instr_response_time', instr_trial.response_time - instr_trial.start_time)
            trial_handler.addData('instr_end_time', instr_trial.end_time)
            trial_handler.addData('instr_type', self.current_instruction.name)
            trial_handler.addData('is_instruction', True)
            self.exp_handler.nextEntry()

            # Check for kill flag
            if self.stopped:
                break

            # Variable to keep track of the number of instruction screens shown
            # Instruction screen IDs are negative. The first shown is -1, the second -2, etc.
            self.n_instructions_shown -= 1

        return instr_trial

    def run(self):
        """ Run the trials that were prepared. The experimental design must be loaded. """

        # Loop through blocks
        for block_n in range(self.start_block, 5):

            # Get the trial handler of the current block
            trial_handler = self.trial_handlers[block_n]

            # Show DEBUG screen first, if we're in debug mode.
            if block_n == self.start_block:
                if self.subject_initials == 'DEBUG':
                    self.instructions_to_show = [self.debug_screen]
                    self.show_instructions(trial_handler=trial_handler, phase_durations=[
                        100])

                # Show welcome screen (only if session was started at block 0)
                if self.start_block == 0:
                    self.instructions_to_show = [self.welcome_screen]  # In list, so show_instructions() can iterate
                    _ = self.show_instructions(trial_handler=trial_handler)

            # If this is not the first block that is run, let operator check if we need to recalibrate.
            # Also the time for a break!
            if block_n > self.start_block:
                end_block_instr = self.show_instructions(trial_handler=trial_handler, end_block=True)

                # Does the operator want to recalibrate or not? If 'r' was pressed: yes, otherwise: no.
                if end_block_instr.stop_key == 'r':
                    if self.tracker is not None:
                        if self.tracker.connected():
                            self.tracker.stop_recording()
                            # pylink.openGraphicsEx(self.tracker.eyelink_graphics)
                            self.tracker_setup()    # Try to setup again

                    else:
                        print('I would recalibrate, but no tracker is connected...')
                        self.instructions_to_show = self.recalibration_error_screen
                        _ = self.show_instructions(trial_handler=trial_handler)

            # Reset all feedback objects of which the text is dynamically changed
            # text (SAT after limbic might otherwise show feedback points)
            self.feedback_text_objects[1].text = 'Correct!'

            # It is useful to save the last trial ID for the current block.
            self.last_ID_this_block = self.design.loc[self.design['block'] == block_n, 'block_trial_ID'].iloc[-1]

            # Loop over block trials
            for trial in trial_handler:

                # If this is the first trial in the block, prepare and show instructions first.
                if trial.block_trial_ID == 0:
                    block_type = trial.block_type
                    response_modality = trial.response_modality
                    respond_possible = True

                    if block_type == 'cognitive_hand':
                        self.instructions_to_show = self.cognitive_hand_instructions
                    elif block_type == 'cognitive_eye':
                        self.instructions_to_show = self.cognitive_eye_instructions
                    elif block_type == 'limbic_hand':
                        self.instructions_to_show = self.limbic_hand_instructions
                    elif block_type == 'limbic_eye':
                        self.instructions_to_show = self.limbic_eye_instructions
                    elif block_type == 'localizer' and response_modality == 'hand':
                        if trial.trial_ID == 0:
                            self.instructions_to_show = self.localizer_instructions_hand_start
                        else:
                            self.instructions_to_show = self.localizer_instructions_hand
                            respond_possible = False
                    elif block_type == 'localizer' and response_modality == 'eye':
                        if trial.trial_ID == 0:
                            self.instructions_to_show = self.localizer_instructions_eye_start
                        else:
                            self.instructions_to_show = self.localizer_instructions_eye
                            respond_possible = False

                    _ = self.show_instructions(trial_handler=trial_handler, respond_possible=respond_possible)

                    # Check for kill flag
                    if self.stopped:
                        break

                # shortcut (needed in all trial types)
                this_phases = (trial.phase_0,  # time to wait for scanner
                               trial.phase_1,  # pre-cue fixation cross
                               trial.phase_2,  # cue
                               trial.phase_3,  # post-cue fixation cross [0 for localizer]
                               trial.phase_4,  # stimulus
                               trial.phase_5,  # post-stimulus time (after response, before feedback)
                               trial.phase_6,  # feedback time
                               trial.phase_7)  # ITI

                # What trial type to run?
                if trial.null_trial:  # True or false
                    if 'eye' in trial.block_type:
                        draw_crosses = True
                    else:
                        draw_crosses = False

                    # Run null trial
                    trial_object = self.run_null_trial(trial, phases=this_phases, draw_crosses=draw_crosses)
                else:
                    if block_n == 0:
                        # Run localizer
                        trial_object = self.run_localizer_trial(trial, phases=this_phases)
                        trial_handler.addData('wrong_modality_answers', trial_object.wrong_modality_answers)
                    else:
                        # Run decision-making trials
                        trial_object = self.run_experimental_trial(trial, phases=this_phases, block_n=block_n)

                        # Save evidence arrays (only in decision-making trials)
                        for flasher in range(self.n_flashers):
                            trial_handler.addData('evidence stream ' + str(flasher),
                                                  self.trial_arrays[trial.trial_ID][flasher][self.first_frame_idx])
                        trial_handler.addData('evidence shown at rt',
                                              trial_object.evidence_shown / self.standard_parameters['flash_length'])
                        trial_handler.addData('total increments shown at rt',
                                              trial_object.total_increments / self.standard_parameters[
                                                  'increment_length'])
                        trial_handler.addData('late responses', trial_object.late_responses)

                    # Save behavioral data (only in non-null trials)
                    trial_handler.addData('rt', trial_object.response_time)
                    trial_handler.addData('response', trial_object.response)
                    trial_handler.addData('response type', trial_object.response_type)
                    trial_handler.addData('correct', trial_object.response_type == 1)
                    trial_handler.addData('feedback', self.feedback_text_objects[trial_object.feedback_type].text)
                    trial_handler.addData('score', self.participant_score)

                if trial.block_trial_ID == 0:
                    block_start_time = trial_object.t_time

                # Add timing for all trial types
                trial_handler.addData('phase_0_measured', trial_object.t_time - trial_object.start_time)
                trial_handler.addData('phase_1_measured', trial_object.fix1_time - trial_object.t_time)
                trial_handler.addData('phase_2_measured', trial_object.cue_time - trial_object.fix1_time)
                trial_handler.addData('phase_3_measured', trial_object.fix2_time - trial_object.cue_time)
                trial_handler.addData('phase_4_measured', trial_object.stimulus_time - trial_object.fix2_time)
                trial_handler.addData('phase_5_measured', trial_object.post_stimulus_time - trial_object.stimulus_time)
                trial_handler.addData('phase_6_measured', trial_object.feedback_time - trial_object.post_stimulus_time)
                trial_handler.addData('duration_measured', trial_object.run_time - (trial_object.t_time -
                                                                                    trial_object.start_time))
                # This is not the "actual" duration, because it does not include the full IIT!

                trial_handler.addData('trial_start_time_block_measured', trial_object.t_time - block_start_time)
                trial_handler.addData('cue_onset_time_block_measured', trial_object.fix1_time - block_start_time)
                # Counter-intuitive, but fix1_time is the END of fixation cross 1 = beginning of cue
                trial_handler.addData('stimulus_onset_time_block_measured', trial_object.fix2_time - block_start_time)
                # Counter-intuitive, but fix2_time is END of fixation cross 2 = onset of stim

                # Trial finished, so on to the next entry
                self.exp_handler.nextEntry()

                # Check for stop flag in trial loop
                if self.stopped:
                    break

            # Check for stop flag in block loop
            if self.stopped:
                break

            # Save data of every block after every block!
            self.save_data(block_n=block_n)

        self.close()

    def save_data(self, block_n=None):
        """ Saves all data and the current frame intervals """

        if block_n is not None:
            output_fn_dat = self.exp_handler.dataFileName + '_block_' + str(block_n)
            output_fn_frames = self.output_file + '_block_' + str(block_n)
        else:
            output_fn_dat = self.exp_handler.dataFileName
            output_fn_frames = self.output_file

        self.exp_handler.saveAsPickle(output_fn_dat)
        self.exp_handler.saveAsWideText(output_fn_dat + '.csv')

        if block_n is not None:
            with open(output_fn_frames + '_outputDict.pickle', 'wb') as f:
                pickle.dump(self.outputDict, f)

        if self.screen.recordFrameIntervals:

            # Save frame intervals to file
            self.screen.saveFrameIntervals(fileName=output_fn_frames + '_frame_intervals.log', clear=False)

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
            pylab.savefig(output_fn_frames + '_frame_intervals.png')

    def close(self):
        """ Saves stuff and closes """

        self.save_data()
        print('Participant scored %d points, which corresponds to %.2f euro or %.2f participant points' % (
            self.participant_score, self.participant_score * (10 / 560), self.participant_score * (1 / 560)))

        super(FlashSession, self).close()


class FlashPracticeSession(EyelinkSession):
    """ Practice session of the FlashTask """

    def __init__(self, subject_initials, index_number, scanner, tracker_on, sound_system=False, language='en'):
        super(FlashPracticeSession, self).__init__(subject_initials, index_number, sound_system)

        # Set-up screen
        screen = self.create_screen(size=screen_res, full_screen=1, physical_screen_distance=159.0,
                                    background_color=background_color, physical_screen_size=(70, 40),
                                    monitor=monitor_name)
        self.screen.monitor = monitors.Monitor(monitor_name)
        self.screen.recordFrameIntervals = record_intervals
        self.mouse = event.Mouse(win=screen, visible=False)

        # For logging: set-up output file name, experiment handler
        self.create_output_file_name(data_directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
        self.output_file = self.output_file + 'PRACTICE'

        # save a log file for detail verbose info
        logFile = logging.LogFile(self.output_file + '.log', level=logging.EXP)

        # Ensure that relative paths start from the same directory as this script
        _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
        self.exp_handler = data.ExperimentHandler(name='flashtaskPractice',
                                                  version='1',
                                                  extraInfo={'subject_initials': subject_initials,
                                                             'index_number': index_number,
                                                             'scanner': scanner,
                                                             'tracker_on': tracker_on},
                                                  runtimeInfo=info.RunTimeInfo,
                                                  dataFileName=os.path.join(_thisDir, self.output_file),
                                                  autoLog=True)
        self.trial_handlers = []
        self.participant_score = 0
        self.n_instructions_shown = -1
        self.current_block = 0
        self.current_block_trial = 0

        # TR of MRI
        self.TR = TR

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
        self.sat_feedback_parameters = sat

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
        self.radius_deg = self.standard_parameters['radius_deg']
        self.flasher_size = self.standard_parameters['flasher_size']

        # Initialize psychopy.visual objects attributes
        self.language = language
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

        # For logging: set-up output file name, experiment handler
        self.create_output_file_name()

        # save a log file for detail verbose info
        logfile = logging.LogFile(self.output_file + '.log', level=logging.EXP)

        # Ensure that relative paths start from the same directory as this script
        _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())

        self.exp_handler = data.ExperimentHandler(name='flashtaskPractice',
                                                  version='1.0',
                                                  extraInfo={'subject_initials': subject_initials,
                                                             'index_number': index_number,
                                                             'scanner': scanner,
                                                             'tracker_on': tracker_on},
                                                  runtimeInfo=info.RunTimeInfo,
                                                  dataFileName=os.path.join(_thisDir, self.output_file),
                                                  autoLog=True)

    def load_design(self):
        # Load full design in self.design
        self.design = pd.read_csv(os.path.join(design_path, 'practice', 'all_blocks', 'trials.csv'))

        # First load localizer block
        localizer_conditions = data.importConditions(
            os.path.join(design_path, 'practice', 'block_0_type_localizer', 'trials.csv'))

        # Append the localizer trial handler to the self.trial_handlers attr
        self.trial_handlers.append(data.TrialHandler(localizer_conditions, nReps=1, method='sequential'))

        # list block directories
        dirs = glob(os.path.join(design_path, 'practice', 'block_*'))

        # Loop over the four blocks and add them, as trial handlers, to the experiment handler
        for block in range(len(dirs)-1):

            # Find path of block design
            path = glob(os.path.join(design_path, 'practice', 'block_%d_*' % (block+1), 'trials.csv'))[0]

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

        # Load all texts
        this_file = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(this_file, 'instructions', self.language, 'welcome_practice.txt'), 'rb') as f:
            welcome_screen_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'practice_block_end_instruction.txt'),
                  'rb') as f:
            practice_block_end_instruction_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'practice_instructions.txt'), 'rb') as f:
            practice_instructions_txt = f.read().split('\n\n\n')

        with open(os.path.join(this_file, 'instructions', self.language, 'end_screen.txt'), 'rb') as f:
            end_screen_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'scanner_wait.txt'), 'rb') as f:
            scanner_wait_txt = f.read().split('\n\n\n')[0]

        with open(os.path.join(this_file, 'instructions', self.language, 'feedback.txt'), 'rb') as f:
            self.feedback_txt = f.read().split('\n\n\n')

        # Prepare fixation cross
        self.fixation_cross = FixationCross(win=self.screen,
                                            inner_radius=fix_cross_parameters['inner_radius_degrees'],
                                            outer_radius=fix_cross_parameters['outer_radius_degrees'],
                                            bg=background_color)

        # Prepare cue
        self.cue_object = visual.TextStim(win=self.screen, text='Cue here', units='cm', height=visual_sizes[
            'cue_object'])

        # Prepare feedback stimuli
        self.feedback_text_objects = [
            # 0 = Too slow
            visual.TextStim(win=self.screen, text=self.feedback_txt[0], color='darkred', units='deg',
                            height=visual_sizes['fb_text']),
            # 1 = correct
            visual.TextStim(win=self.screen, text=self.feedback_txt[1], color='darkgreen', units='deg',
                            height=visual_sizes['fb_text']),
            # 2 = wrong
            visual.TextStim(win=self.screen, text=self.feedback_txt[2], color='darkred', units='deg',
                            height=visual_sizes['fb_text']),
            # 3 = too fast
            visual.TextStim(win=self.screen, text=self.feedback_txt[3], color='darkred', units='deg',
                            height=visual_sizes['fb_text']),
            # 4 = early phase
            visual.TextStim(win=self.screen, text=self.feedback_txt[4], color='darkred', units='deg',
                            height=visual_sizes['fb_text']),
        ]

        # Prepare localizer stimuli
        arrow_right_vertices = [(-0.2, 0.05), (-0.2, -0.05), (-.0, -0.05), (0, -0.1), (0.2, 0), (0, 0.1), (0, 0.05)]
        arrow_left_vertices = [(0.2, 0.05), (0.2, -0.05), (0.0, -0.05), (0, -0.1), (-0.2, 0), (0, 0.1), (0, 0.05)]
        arrow_neutral_vertices = [(0.2, 0.0),  # Right point
                                  (0.1, 0.1),  # Towards up, left
                                  (0.1, 0.05),  # Down
                                  (-0.1, 0.05),  # Left
                                  (-0.1, 0.1),  # Up
                                  (-0.2, 0.0),  # Left point
                                  (-0.1, -0.1),  # Down, right
                                  (-0.1, -0.05),  # Up
                                  (0.1, -0.05),  # Right
                                  (0.1, -0.1)]  # Down

        self.arrow_stimuli = [
            visual.ShapeStim(win=self.screen, vertices=arrow_left_vertices, fillColor='lightgray',
                             size=visual_sizes['arrows'], lineColor='lightgray', units='deg'),
            visual.ShapeStim(win=self.screen, vertices=arrow_right_vertices, fillColor='lightgray',
                             size=visual_sizes['arrows'], lineColor='lightgray', units='deg'),
            visual.ShapeStim(win=self.screen, vertices=arrow_neutral_vertices, fillColor='lightgray',
                             size=visual_sizes['arrows'], lineColor='lightgray', units='deg')
        ]

        self.crosses = [
            visual.TextStim(win=self.screen, text='+', pos=(-8, 0), height=visual_sizes['crosses'], units='deg'),
            visual.TextStim(win=self.screen, text='+', pos=(8, 0), height=visual_sizes['crosses'], units='deg')
        ]

        # Prepare waiting for scanner-screen
        self.scanner_wait_screen = visual.TextStim(win=self.screen,
                                                   text=scanner_wait_txt,
                                                   units='pix', font='Helvetica Neue', pos=(0, 0),
                                                   italic=True, height=30, alignHoriz='center', )

        # Keep debug screen at hand
        self.debug_screen = visual.TextStim(win=self.screen,
                                            text='DEBUG MODE. DO NOT RUN AN ACTUAL EXPERIMENT',
                                            color='darkred', height=1, units='cm')

        # Prepare welcome screen
        self.welcome_screen = visual.TextStim(win=self.screen,
                                              text=welcome_screen_txt,
                                              units='pix', font='Helvetica Neue', pos=(0, 0),
                                              italic=False, height=30, alignHoriz='center', )

        self.practice_block_end_instruction = [
            visual.TextStim(win=self.screen,
                                text=practice_block_end_instruction_txt,
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
            ]

        # Prepare instruction screens
        self.practice_instructions = [
            [
                # First, hand localizer with feedback.
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[0],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
            ],
            [   # Hand localizer without feedback
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[1],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
            ],
            [   # Eye localizer without feedback.
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[2],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
            ],
            [   # Flashing circles without cue, hand response, increasing difficulty.
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[3],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
            ],
            [   # Flashing circles with SAT-cue, hand response.
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[4],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
            ],
            [   # Flashing circles with SAT-cue, eye response.
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[5],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
            ],
            [   # Flashing circles with bias-cue, hand response.
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[6],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[7],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[8],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[9],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix')
            ],
            [  # Flashing circles with bias-cue, eye response.
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[10],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[7],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[8],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix'),
                visual.TextStim(win=self.screen,
                                text=practice_instructions_txt[11],
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix')
            ],
        ]

        self.end_screen = visual.TextStim(
                                win=self.screen,
                                text=end_screen_txt,
                                font='Helvetica Neue', pos=(0, 0),
                                italic=False, height=30, alignHoriz='center', units='pix')

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
        else:  # else start from 0.5*pi (== (1,0))
            t = 0.5 * np.pi

        radius_cm = self.centimeters_per_degree * self.radius_deg
        pos_x = radius_cm * np.cos(t + np.arange(1, self.n_flashers + 1) * 2 * np.pi / self.n_flashers)
        pos_y = radius_cm * np.sin(t + np.arange(1, self.n_flashers + 1) * 2 * np.pi / self.n_flashers)
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

        # Get the number of trials from the design; this is the the number of rows in the DataFrame.
        self.n_trials = self.design.shape[0]

        # Get the maximum duration a stimulus is shown
        self.stim_max_time = self.design.loc[self.design['block_type'] != 'localizer', 'phase_4'].max()

        # Make sure the correct_answers are extracted from the design
        self.correct_answers = self.design['correct_answer'].values.astype(int)

        # Define which flashing circle is correct in all n_trials
        self.incorrect_answers = [np.delete(np.arange(self.n_flashers), i) for i in self.correct_answers if i in
                                  np.arange(self.n_flashers)]

        # How many increments can we show during the stimulus period, with the specified increment_length and current
        # frame rate?
        n_increments = np.ceil(self.stim_max_time * self.frame_rate / increment_length).astype(int)
        n_increments += 1  # 1 full increment extra, in case we're dropping frames

        # Knowing this, we can define an index mask to select all frames that correspond to the between-increment
        # pause period
        mask_idx = np.tile(np.hstack((np.repeat([0], repeats=flash_length),
                                      np.repeat([1], repeats=pause_length))),
                           n_increments).astype(bool)

        # # Which responses (keys or saccades) correspond to these flashers?
        # self.correct_responses = np.array(self.response_keys)[self.correct_answers]
        # self.incorrect_responses = [self.response_keys[self.incorrect_answers[i]] for i in range(n_trials)]

        # Initialize 'increment arrays' for correct and incorrect. These are arrays filled with 0s and 1s, determining
        # for each 'increment' whether a piece of evidence is shown or not.
        # (this is a bit loopy, but I can't be bothered to make nice matrices here)
        current_difficulty = (0.9, 0.2)
        self.trial_arrays = []
        for trial_n in range(self.n_trials):

            # If the current trial is a null trial, or is a localizer trial, don't make an evidence array
            if self.design.iloc[trial_n]['null_trial'] or self.design.iloc[trial_n]['block_type'] == 'localizer':
                self.trial_arrays.append(None)
                continue

            if self.design.iloc[trial_n]['block'] == 3:
                # In the first block, we start out with very easy trials, and make it easier every 4 trials (total 16
                #  trials).
                if self.design.iloc[trial_n]['block_trial_ID'] % 4 == 0:
                    current_difficulty = (current_difficulty[0]-0.05, current_difficulty[1]+0.05)

                prop_correct_this_trial = current_difficulty[0]
                prop_incorrect_this_trial = current_difficulty[1]
            else:
                prop_correct_this_trial = prop_correct
                prop_incorrect_this_trial = prop_incorrect

            corr_answer_this_trial = self.correct_answers[trial_n]  # shortcut

            # Ensure that, at the end of the trial, there is more evidence for the correct choice alternative than for
            # any of the other choice alternatives
            good_evidence_streams = False
            while not good_evidence_streams:
                evidence_streams_this_trial = []
                total_evidence_per_flasher = []
                for i in range(self.n_flashers):

                    # First, create initial evidence stream
                    if i == corr_answer_this_trial:
                        evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_correct_this_trial,
                                                                          size=n_increments).astype(
                            np.int8)
                    else:
                        evidence_stream_this_flasher = np.random.binomial(n=1, p=prop_incorrect_this_trial,
                                                                          size=n_increments).astype(np.int8)

                    # How many pieces of evidence are shown in total for this flasher?
                    total_evidence_per_flasher.append(np.sum(evidence_stream_this_flasher))

                    # Repeat every increment for n_frames
                    evidence_stream_this_flasher = np.repeat(evidence_stream_this_flasher, increment_length)
                    evidence_stream_this_flasher[mask_idx] = 0  # add pause

                    evidence_streams_this_trial.append(evidence_stream_this_flasher)

                # Check if the evidence for the correct flasher is at least the evidence for each other flasher
                total_evidence_per_flasher = np.array(total_evidence_per_flasher)
                mask = np.ones(total_evidence_per_flasher.shape[0], np.bool)  # Create mask: compare correct to others
                mask[corr_answer_this_trial] = 0
                if (total_evidence_per_flasher[corr_answer_this_trial] >= total_evidence_per_flasher)[mask].all():
                    good_evidence_streams = True

            self.trial_arrays.append(evidence_streams_this_trial)

        # Create new mask to select only first frame of every increment
        self.first_frame_idx = np.arange(0, mask_idx.shape[0], increment_length)

    def run_localizer_trial(self, trial, phases):
        """ Runs a single localizer trial """

        if trial.response_modality == 'hand':
            trial_pointer = LocalizerTrialKeyboard
        elif trial.response_modality == 'eye':
            trial_pointer = LocalizerTrialSaccade
        else:
            raise (ValueError('The trial response type is not understood. %s was provided, but ''eye'' or '
                              'hand'' is expected. Trial n: %d, block n: 0' % (trial.response_modality,
                                                                               trial.trial_ID)))

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
            raise (ValueError('The trial response type is not understood. %s was provided, but ''eye'' or '
                              'hand'' is expected. Trial n: %d, block n: %d' % (trial.response_modality,
                                                                                trial.trial_ID,
                                                                                trial.block_num)))

        # In a limbic trial, prepare / update feedback
        if 'limbic' in trial.block_type:
            if this_trial_type in [0, 1]:  # Neutral condition
                self.feedback_text_objects[1].text = self.feedback_txt[1]
            elif this_trial_type in [2, 5]:  # Compatible cue condition
                self.feedback_text_objects[1].text = self.feedback_txt[1] + ' +8\n' + self.feedback_txt[6] + ' %d' % (
                    self.participant_score + 8)
            elif this_trial_type in [3, 4]:  # Incompatible cue condition
                self.feedback_text_objects[1].text = self.feedback_txt[1] + ' +2\n' + self.feedback_txt[6] + ' %d' % (
                    self.participant_score + 2)

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
                self.participant_score += 8
            elif this_trial_type in [3, 4]:
                self.participant_score += 2

        return trial_object

    def show_instructions(self):
        """ Shows current instructions """

        self.stop_instructions = False

        # Loop over self.current_instructions
        for instruction_n in range(len(self.instructions_to_show)):
            self.current_instruction = self.instructions_to_show[instruction_n]
            FlashInstructionsPractice(ID=self.n_instructions_shown,
                                      parameters={},
                                      phase_durations=self.instructions_durations,
                                      session=self,
                                      screen=self.screen,
                                      tracker=self.tracker).run()

            # Check for kill flag
            if self.stopped:
                break

            if self.stop_instructions:
                break

        # Variable to keep track of the number of instruction screens shown
        # Instruction screen IDs are negative. The first shown is -1, the second -2, etc.
        self.n_instructions_shown -= 1

    def run(self):
        """ Run the trials that were prepared. The experimental design must be loaded. """

        # Show DEBUG screen first, if we're in debug mode.
        if self.subject_initials == 'DEBUG':
            self.current_instruction = self.debug_screen
            FlashInstructions(ID=-99, parameters={},
                              phase_durations=[100],
                              session=self,
                              screen=self.screen,
                              tracker=self.tracker).run()

        # Show welcome screen
        self.instructions_to_show = [self.welcome_screen]  # In list, so show_instructions() can iterate
        self.show_instructions()

        # Loop through blocks
        while not self.stopped:
            print('Starting block %d' % self.current_block)

            # if self.current_block == 3:
            #     self.scanner = 'n'
            # else:
            #     self.scanner = 'y'

            # Find path of block design
            path = glob(os.path.join(design_path, 'practice', 'block_%d_*' % self.current_block, 'trials.csv'))[0]

            # Create trial handler, and append to experiment handler
            trial_handler = data.TrialHandler(data.importConditions(path), nReps=1, method='sequential')

            # Reset all feedback objects of which the text is dynamically changed
            # text (SAT after limbic might otherwise show feedback points)
            self.feedback_text_objects[1].text = 'Correct!'

            # It is useful to save the last trial ID for the current block.
            self.last_ID_this_block = self.design.loc[self.design['block'] == self.current_block, 'block_trial_ID'].iloc[-1]

            # Loop over block trials
            for trial in trial_handler:

                # If this is the first trial in the block, prepare and show instructions first.
                if trial.block_trial_ID == 0:
                    self.instructions_to_show = self.practice_instructions[self.current_block]
                    self.show_instructions()

                    if self.stop_instructions:
                        break

                    # Check for kill flag
                    if self.stopped:
                        break

                # shortcut (needed in all trial types)
                this_phases = (trial.phase_0,  # time to wait for scanner
                               trial.phase_1,  # pre-cue fixation cross
                               trial.phase_2,  # cue
                               trial.phase_3,  # post-cue fixation cross [0 for localizer]
                               trial.phase_4,  # stimulus
                               trial.phase_5,  # post-stimulus time (after response, before feedback)
                               trial.phase_6,  # feedback time
                               trial.phase_7)  # ITI

                # What trial type to run?
                if trial.block_type == 'localizer':   # Localizer
                    trial_object = self.run_localizer_trial(trial, phases=this_phases)   # RUN LOCALIZER
                else:              # Experiment
                    trial_object = self.run_experimental_trial(trial, phases=this_phases,
                                                               block_n=self.current_block)  # RUN

                    # Save evidence arrays (only in experimental trials)
                    for flasher in range(self.n_flashers):
                        trial_handler.addData('evidence stream ' + str(flasher),
                                              self.trial_arrays[trial.trial_ID][flasher][self.first_frame_idx])
                    trial_handler.addData('evidence shown at rt',
                                          trial_object.evidence_shown / self.standard_parameters['flash_length'])

                # Save all data (only in non-null trials)
                trial_handler.addData('rt', trial_object.response_time)
                trial_handler.addData('response', trial_object.response)
                trial_handler.addData('response type', trial_object.response_type)
                trial_handler.addData('correct', trial_object.response_type == 1)
                trial_handler.addData('feedback', self.feedback_text_objects[trial_object.feedback_type].text)
                trial_handler.addData('score', self.participant_score)

                # Trial finished, so on to the next entry
                self.exp_handler.nextEntry()

                # Check for stop flag in trial loop
                if self.stopped:
                    break

            # Check for stop flag in block loop
            if self.stopped:
                break

            if self.stop_instructions:
                continue

            # Update block
            if self.current_block < 7:
                self.current_block += 1

                if self.current_block > 0:
                    self.instructions_to_show = self.practice_block_end_instruction
                    self.show_instructions()
            else:
                # Final block reached
                self.instructions_to_show = [self.end_screen]
                self.show_instructions()
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

        super(FlashPracticeSession, self).close()
