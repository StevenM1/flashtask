#!/usr/bin/env python
# encoding: utf-8
from exp_tools import Trial
from psychopy import event
import numpy as np
from scipy import stats


class FlashTrial(Trial):
    """ Class that runs a single FlashTrial. Parent for FlashTrialSaccade and FlashTrialKeyboard, which should
    actually be initiadted (rather than this class).

    This class assumes that all visual objects (flashing circles, cues, feedback texts, target crosses,
    fixation cross) are attributes of the Session. This greatly improves speed, as these only have to be initiated
    once instead of at the start of every trial.

    A FlashTrial consists of the following phases:
    0. Wait for scanner pulse
    1. Pre-cue fixation cross (should be jittered)
    2. Cue (arrow left/right)
    3. Post-cue fixation cross (should be jittered)
    4. Stimulus & Response (Flashing Circles are shown, participant makes eye movement / button press)
    5. Feedback
    6. ITI

    Parameters
    ----------
    ID: int
        ID number of trial
    block_trial_ID: int
        Number of trial within the current block
    parameters: dict
        Dictionary containing parameters that specify what is drawn. Needs:
            1. "correct_answer" (0 or 1), which specifies the direction of the stimulus (and response).
            2. trial_evidence_arrays: a list of np.arrays, which contains 0 and 1s determining for every frame
            whether a circle needs to be shown or not. See FlashSession.prepare_trials for more details on how this
            works.
            3. cue: str ['LEFT', 'RIGHT', 'NEUTRAL', 'SPD', 'ACC']. If left/right/neutral, an arrow is drawn. If
            SPD/ACC, an instruction is shown with SPD or ACC.
    phase_durations : list
        List specifying the durations of each phase of this trial.
    session: exp_tools.Session instance
    screen: psychopy.visual.Window instance
    tracker: pygaze.EyeTracker object
        Passed on to parent class

    Attributes
    -----------
    response_type: int
        Specifies what kind of response was given:
        0 = Too slow  (no answer given at end of stimulus presentation)
        1 = Correct
        2 = Wrong
        3 = Too fast
        4 = Too early (early phase response) - does not exist in FlashTrial, but exists for compatibility with
        LocalizerPractice
    response_time: float
        Reaction time. Note that, for the child class FlashTrialSaccade, this is NOT ACCURATE!
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None,
                 tracker=None):
        super(FlashTrial, self).__init__(parameters=parameters, phase_durations=phase_durations, session=session,
                                         screen=screen, tracker=tracker)
        self.ID = ID
        self.block_trial_ID = block_trial_ID
        self.frame_n = -1
        self.response = None
        self.draw_crosses = False

        self.response_type = 0   # 0 = no response, 1 = correct, 2 = wrong, 3 = too early
        self.feedback_type = 0   # 0 = too late, 1 = correct, 2 = wrong, 3 = too early
        self.stimulus = self.session.stimulus
        self.stimulus.trial_evidence_arrays = parameters['trial_evidence_arrays']
        self.evidence_shown = np.repeat([0], self.session.n_flashers)
        self.total_increments = 0
        self.cuetext = None
        self.late_responses = []

        # keep track of number of TRs recorded. Only end trial if at least 2 TRs are recorded (3 TRs per trial).
        self.n_TRs = 0

        # Initialize cue. This is a bit of a hacky workaround in order to be able to use this class for both conditions
        if 'cue' in parameters.keys():
            self.cuetext = parameters['cue']
            if self.cuetext in ['LEFT', 'RIGHT', 'NEU']:
                if self.cuetext == 'LEFT':
                    self.cue = self.session.arrow_stimuli[0]
                elif self.cuetext == 'RIGHT':
                    self.cue = self.session.arrow_stimuli[1]
                elif self.cuetext == 'NEU':
                    self.cue = self.session.arrow_stimuli[2]
            else:
                self.cue = self.session.cue_object
                self.cue.text = self.cuetext
        else:
            cuetext = 'Warning! No cue passed to trial!'
            self.cue = self.session.cue_object
            self.cue.text = cuetext

        # Initialize times
        self.run_time = 0.0
        self.t_time = self.fix1_time = self.cue_time = self.fix2_time = self.stimulus_time = self.post_stimulus_time \
            = self.feedback_time = self.ITI_time = 0.0
        self.response_time = None

    def draw(self):
        """ Draws the current frame """

        if self.phase == 0:   # waiting for scanner-time
            if self.block_trial_ID == 0:
                self.session.scanner_wait_screen.draw()  # Only show this before the first trial
            else:
                self.session.fixation_cross.draw()
                if self.draw_crosses:
                    self.session.crosses[0].draw()
                    self.session.crosses[1].draw()
        elif self.phase == 1:  # Pre-cue fix cross
            self.session.fixation_cross.draw()
            if self.draw_crosses:
                self.session.crosses[0].draw()
                self.session.crosses[1].draw()
                # if not os.path.isfile('screenshot_trial_fixcross.png'):
            #     self.session.screen.flip()
            #     self.session.screen.getMovieFrame()
            #     self.session.screen.saveMovieFrames('screenshot_trial_fixcross.png')
        elif self.phase == 2:  # Cue
            self.cue.draw()
            if self.draw_crosses:
                self.session.crosses[0].draw()
                self.session.crosses[1].draw()
                # if not os.path.isfile('screenshot_trial_cue_' + self.cuetext + '.png'):
            #     self.session.screen.flip()
            #     self.session.screen.getMovieFrame()
            #     self.session.screen.saveMovieFrames('screenshot_trial_cue_' + self.cuetext + '.png')

        elif self.phase == 3:  # post-cue fix cross
            self.session.fixation_cross.draw()
            if self.draw_crosses:
                self.session.crosses[0].draw()
                self.session.crosses[1].draw()
        elif self.phase == 4:  # stimulus
            self.session.fixation_cross.draw()
            shown_opacities = self.stimulus.draw(frame_n=self.frame_n)
            self.evidence_shown = self.evidence_shown + shown_opacities
            self.total_increments += 1
            if self.draw_crosses:
                self.session.crosses[0].draw()
                self.session.crosses[1].draw()
            # if self.stimulus.trial_evidence_arrays[0][self.frame_n] == 1 and self.stimulus.trial_evidence_arrays[1][
            #     self.frame_n] == 1:
            #     if not os.path.isfile('screenshot_trial_stim.png'):
            #         self.session.screen.flip()
            #         self.session.screen.getMovieFrame()
            #         self.session.screen.saveMovieFrames('screenshot_trial_stim.png')

        elif self.phase == 5:  # post-stimulus fill time
            self.session.fixation_cross.draw()
            self.stimulus.draw(frame_n=self.frame_n, continuous=False)  # Continuous creates constant streams of flashes
            if self.draw_crosses:
                self.session.crosses[0].draw()
                self.session.crosses[1].draw()
        elif self.phase == 6:  # feedback
            self.session.feedback_text_objects[self.feedback_type].draw()
            if self.draw_crosses:
                self.session.crosses[0].draw()
                self.session.crosses[1].draw()
            # fb_name = self.session.feedback_text_objects[self.feedback_type].text
            # if not os.path.isfile('screenshot_trial_feedback_' + fb_name[0] + fb_name[-2] + '.png'):
            #     self.session.screen.flip()
            #     self.session.screen.getMovieFrame()
            #     self.session.screen.saveMovieFrames('screenshot_trial_feedback_' + fb_name[0] + fb_name[-2] + '.png')
        elif self.phase == 7:
            self.session.fixation_cross.draw()
            if self.draw_crosses:
                self.session.crosses[0].draw()
                self.session.crosses[1].draw()

        super(FlashTrial, self).draw()

    def event(self):
        """ Event-checking is determined by the subclass (either check for keyboard responses or a saccade) """
        pass

    def phase_forward(self):
        """ Call the superclass phase_forward method first, and reset the current frame number to 0 """
        super(FlashTrial, self).phase_forward()
        self.phase_time = self.session.clock.getTime()
        self.frame_n = 0

    def run(self):
        super(FlashTrial, self).run()

        while not self.stopped:
            self.frame_n += 1
            self.run_time = self.session.clock.getTime() - self.start_time

            # Fixation cross: waits for scanner pulse!
            if self.phase == 0:
                self.t_time = self.session.clock.getTime()
                if self.session.scanner == 'n':
                    self.phase_forward()

            # In phase 1, we show the cue
            if self.phase == 1:
                self.fix1_time = self.session.clock.getTime()
                if (self.fix1_time - self.t_time) > self.phase_durations[1]:
                    self.phase_forward()

            # In phase 2, we show the cue
            if self.phase == 2:
                self.cue_time = self.session.clock.getTime()
                if (self.cue_time - self.fix1_time) > self.phase_durations[2]:
                    self.phase_forward()

            # In phase 3, we show the fix cross again
            if self.phase == 3:
                self.fix2_time = self.session.clock.getTime()
                if (self.fix2_time - self.cue_time) > self.phase_durations[3]:
                    self.phase_forward()

            # In phase 4, the stimulus is presented and the participant can respond
            if self.phase == 4:
                self.stimulus_time = self.session.clock.getTime()
                if (self.stimulus_time - self.fix2_time) > self.phase_durations[4]:
                    self.phase_forward()

            # In phase 5, the stimulus is presented, participant has responded
            if self.phase == 5:
                self.post_stimulus_time = self.session.clock.getTime()
                # if self.session.scanner == 'n':  # Outside the scanner we can just move on
                #     self.phase_forward()
                # else:
                if (self.post_stimulus_time - self.fix2_time) > self.phase_durations[4]:  # Use phase_durations[4]!!
                    self.phase_forward()

            # Phase 6 reflects feedback
            if self.phase == 6:
                self.feedback_time = self.session.clock.getTime()
                if (self.feedback_time - self.post_stimulus_time) > self.phase_durations[6]:
                    self.phase_forward()  # keep track of timing

            # Finally, we show ITI
            if self.phase == 7:
                self.ITI_time = self.session.clock.getTime()

                if self.block_trial_ID == self.session.last_ID_this_block or self.session.scanner == 'n':
                    # If this is the last trial of the block, show the FULL ITI
                    print('Trial number %d (block trial %d)' % (self.ID, self.block_trial_ID))
                    print('Actively showing full ITI')
                    if self.ITI_time - self.feedback_time > self.phase_durations[7]:
                        self.stopped = True

                else:
                    # Only allow stopping if at least 3 TRs are recorded (including the start-volume!)
                    # The rest of the ITI is used for preparing the next trial.
                    if self.n_TRs >= 3:
                        self.stopped = True

            # events and draw
            if not self.stopped:
                self.event()
                self.draw()

        self.stop()


# The next two classes handle reponses via keyboard or saccades
class FlashTrialSaccade(FlashTrial):
    """
    FlashTrial on which participants respond by eye movements

    Currently, can only handle TWO flashers / choice options!
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None,
                 tracker=None):
        super(FlashTrialSaccade, self).__init__(ID, block_trial_ID=block_trial_ID, parameters=parameters,
                                                phase_durations=phase_durations,
                                                session=session, screen=screen, tracker=tracker)

        self.correct_direction = parameters['correct_answer']
        self.directions_verbose = ['left saccade', 'right saccade']
        self.eye_movement_detected_in_phase = False
        self.eye_pos_start_phase = [None, None, None, None, None, None, None, None]
        self.draw_crosses = False

    def event(self):
        """ Checks for saccades as answers and keyboard responses for escape / scanner pulse """

        # First check keyboard responses for kill signals and/or scanner pulses
        for i, (ev, ev_time) in enumerate(event.getKeys(timeStamped=self.session.clock)):

            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, ev_time, 'escape: user killed session'])
                    self.stopped = True
                    self.session.stopped = True
                    print('Session stopped!')

                elif ev == 'equal':
                    self.events.append([-99, ev_time - self.start_time, 'user skipped trial'])
                    self.stopped = True
                    print('Trial canceled by user')

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])
                    self.n_TRs += 1

                    if self.phase == 0:
                        self.phase_forward()

        # Make sure to get eye position at the start of each phase
        if self.eye_pos_start_phase[self.phase] is None:
            eyepos = self.session.eye_pos()
            distance_from_center = np.divide(np.sqrt((eyepos[0]-self.session.screen_pix_size[0]/2)**2 +
                                                     (eyepos[1]-self.session.screen_pix_size[1]/2)**2),
                                             self.session.pixels_per_degree)
            if distance_from_center < 6:
                # If the distance from the center is less than 6 degrees, we are probably not in a blink. We can
                # accept the current position as the start position
                self.eye_pos_start_phase[self.phase] = self.session.eye_pos()
            else:
                # Distance from center > 8: subject is probably blinking. Do not accept, wait for next frame.
                return

        if not self.eye_movement_detected_in_phase:
            # Get eye position
            eyepos = self.session.eye_pos()
            eyepos_time = self.session.clock.getTime()

            # We calculate the distance travelled from the eye position at the start of this phase.
            center = self.eye_pos_start_phase[self.phase]
            distance_from_center = np.divide(np.sqrt((eyepos[0]-center[0])**2 +
                                                     (eyepos[1]-center[1])**2),
                                             self.session.pixels_per_degree)

            if distance_from_center >= self.session.eye_travel_threshold:
                self.eye_movement_detected_in_phase = True

                # Is the final xpos left or right from initial position?  left = 0, right = 1
                saccade_direction = 0 if eyepos[0] < center[0] else 1
                saccade_direction_verbose = self.directions_verbose[saccade_direction]

                if self.phase == 1:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during fixation cross 1'])

                elif self.phase == 2:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during cue'])

                elif self.phase == 3:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during fixation cross 2'])

                elif self.phase == 4:
                    self.response = saccade_direction_verbose
                    self.response_time = eyepos_time - self.fix2_time

                    # Check for early response
                    if self.response_time < 0.150:  # (seconds)
                        self.feedback_type = 3  # Too fast

                        if saccade_direction == self.correct_direction:
                            self.response_type = 1
                            self.events.append([saccade_direction_verbose, eyepos_time, 'too fast response', 'correct'])
                        else:
                            self.response_type = 2
                            self.events.append([saccade_direction_verbose, eyepos_time, 'too fast response',
                                                'incorrect'])
                    else:
                        # In SPEED conditions, make "too slow"-feedback probabilistic
                        if self.cuetext == 'SPD' and np.random.binomial(n=1, p=stats.expon.cdf(
                                self.response_time, loc=.75, scale=1 / 2.75)):
                            self.feedback_type = 0
                            if saccade_direction == self.correct_direction:
                                self.response_type = 1
                                self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade',
                                                    'correct, too slow feedback'])
                            else:
                                self.response_type = 2
                                self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade',
                                                    'incorrect, too slow feedback'])
                        else:
                            # If fast enough in speed condition, or in non-speed condition, normal feedback
                            if saccade_direction == self.correct_direction:
                                self.response_type = 1
                                self.feedback_type = 1
                                self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade',
                                                    'correct'])
                            else:
                                self.response_type = 2
                                self.feedback_type = 2
                                self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade',
                                                    'incorrect'])

                    self.phase_forward()  # End stimulus presentation when saccade is detected (this will be removed)

                elif self.phase == 5:
                    self.late_responses.append((saccade_direction, eyepos_time - self.fix2_time))
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during post-stimulus fill time'])  #
                    # This will probably always be detected: drift correction?

                elif self.phase == 6:
                    self.late_responses.append((saccade_direction, eyepos_time - self.fix2_time))
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during feedback'])  # This will
                    # probably always be detected: drift correction?

                elif self.phase == 7:
                    self.late_responses.append((saccade_direction, eyepos_time - self.fix2_time))
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during ITI'])  # This will
                    # probably always be detected: drift correction?

    def phase_forward(self):
        """ Do everything the superclass does, but also reset current phase eye movement detection """
        super(FlashTrialSaccade, self).phase_forward()
        self.eye_movement_detected_in_phase = False


class FlashTrialKeyboard(FlashTrial):
    """
    FlashTrial on which participants respond with a keypress
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None,
                 tracker=None):
        super(FlashTrialKeyboard, self).__init__(ID, block_trial_ID=block_trial_ID, parameters=parameters,
                                                 phase_durations=phase_durations,
                                                 session=session, screen=screen, tracker=tracker)

        self.correct_answer = parameters['correct_answer']
        self.correct_key = self.session.response_keys[self.correct_answer]

    def event(self):
        """ Checks for the keyboard responses only """

        for i, (ev, ev_time) in enumerate(event.getKeys(timeStamped=self.session.clock)):
            # ev_time is the event timestamp relative to the Session Clock

            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, ev_time, 'escape: user killed session'])
                    self.stopped = True
                    self.session.stopped = True
                    print('Session stopped!')

                elif ev == 'equal':
                    self.events.append([-99, ev_time - self.start_time, 'user skipped trial'])
                    self.stopped = True
                    print('Trial canceled by user')

                elif ev in self.session.response_keys:

                    if self.phase == 1:
                        self.events.append([ev, ev_time, 'early keypress during fix cross 1'])

                    elif self.phase == 2:
                        self.events.append([ev, ev_time, 'early keypress during cue'])

                    elif self.phase == 3:
                        self.events.append([ev, ev_time, 'early keypress during fix cross 2'])

                    elif self.phase == 4:

                        if i == 0:  # First keypress
                            self.response = ev
                            self.response_time = ev_time - self.fix2_time

                            # Check for early response
                            if self.response_time < 0.150:
                                self.feedback_type = 3  # Too fast

                                if ev == self.correct_key:
                                    self.response_type = 1
                                    self.events.append([ev, ev_time, 'too fast response', 'correct',
                                                        self.response_time])
                                else:
                                    self.response_type = 2
                                    self.events.append([ev, ev_time, 'too fast response', 'incorrect',
                                                        self.response_time])
                            else:
                                # In SPEED conditions, make "too slow"-feedback probabilistic
                                if self.cuetext == 'SPD' and np.random.binomial(n=1, p=stats.expon.cdf(
                                        self.response_time, loc=.75, scale=1/2.75)):
                                    self.feedback_type = 0
                                    if ev == self.correct_key:
                                        self.response_type = 1
                                        self.events.append([ev, ev_time, 'first keypress', 'correct, too slow feedback',
                                                            self.response_time])
                                    else:
                                        self.response_type = 2
                                        self.events.append([ev, ev_time, 'first keypress', 'incorrect, '
                                                                                           'too slow feedback',
                                                            self.response_time])
                                else:
                                    if ev == self.correct_key:
                                        self.response_type = 1
                                        self.feedback_type = 1
                                        self.events.append([ev, ev_time, 'first keypress', 'correct',
                                                            self.response_time])
                                    else:
                                        self.response_type = 2
                                        self.feedback_type = 2
                                        self.events.append([ev, ev_time, 'first keypress', 'incorrect',
                                                            self.response_time])

                            self.phase_forward()
                        else:
                            self.events.append([ev, ev_time, 'late keypress (during stimulus)'])

                    elif self.phase == 5:
                        self.late_responses.append((ev, ev_time-self.fix2_time))
                        self.events.append([ev, ev_time, 'late keypress (during post-stimulus fill time)'])

                    elif self.phase == 6:
                        self.late_responses.append((ev, ev_time-self.fix2_time))
                        self.events.append([ev, ev_time, 'late keypress (during feedback)'])

                    elif self.phase == 7:
                        self.late_responses.append((ev, ev_time-self.fix2_time))
                        self.events.append([ev, ev_time, 'late keypress (during ITI)'])

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])
                    self.n_TRs += 1

                    if self.phase == 0:
                        self.phase_forward()
