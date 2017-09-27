#!/usr/bin/env python
# encoding: utf-8
from exp_tools import Trial
from psychopy import visual, event, logging
import numpy as np


class FlashTrial(Trial):
    """ Class that holds the draw() and run() methods for a FlashTrial.

    The event() method determines the response type (manual keypress vs saccadic), and is constructed in a subclass (
    see below).
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashTrial, self).__init__(parameters=parameters, phase_durations=phase_durations, session=session,
                                         screen=screen, tracker=tracker)
        self.ID = ID
        self.block_trial_ID = block_trial_ID
        self.frame_n = -1
        self.response = None

        self.response_type = 0   # 0 = too late, 1 = correct, 2 = incorrect response
        self.stimulus = self.session.stimulus
        self.stimulus.trial_evidence_arrays = parameters['trial_evidence_arrays']
        self.evidence_shown = np.repeat([0], self.session.n_flashers)

        # Initialize cue. This is a bit of a hacky workaround in order to be able to use this class for both conditions
        if 'cue' in parameters.keys():
            cuetext = parameters['cue']
            if cuetext in ['LEFT', 'RIGHT', 'NEU']:
                if cuetext == 'LEFT':
                    self.cue = self.session.arrow_stimuli[0]
                elif cuetext == 'RIGHT':
                    self.cue = self.session.arrow_stimuli[1]
                elif cuetext == 'NEU':
                    self.cue = self.session.arrow_stimuli[2]
            else:
                self.cue = self.session.cue_object
                self.cue.text = cuetext
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
        elif self.phase == 1:  # Pre-cue fix cross
            self.session.fixation_cross.draw()
        elif self.phase == 2:  # Cue
            self.cue.draw()
        elif self.phase == 3:  # post-cue fix cross
            self.session.fixation_cross.draw()
        elif self.phase == 4:  # stimulus
            shown_opacities = self.stimulus.draw(frame_n=self.frame_n)
            self.evidence_shown = self.evidence_shown + shown_opacities
        elif self.phase == 5:  # post-stimulus fill time
            self.stimulus.draw(frame_n=self.frame_n, continuous=False)  # Continuous creates constant streams of flashes
        elif self.phase == 6:  # feedback
            self.session.feedback_text_objects[self.response_type].draw()

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
                if self.session.scanner == 'n':  # Outside the scanner we can just move on
                    self.phase_forward()
                else:
                    if (self.post_stimulus_time - self.fix2_time) > self.phase_durations[4]:  # Use phase_durations[4]!!
                        self.phase_forward()

            # Phase 6 reflects feedback
            if self.phase == 6:
                self.feedback_time = self.session.clock.getTime()
                if (self.feedback_time - self.post_stimulus_time) > self.phase_durations[6]:
                    self.phase_forward()  # keep track of timing
                    self.stopped = True

            # # Finally, we show ITI
            # if self.phase == 7:
            #     self.ITI_time = self.session.clock.getTime()
            #     if (self.ITI_time - self.feedback_time) > self.phase_durations[6]:
            #         self.stopped = True

            # events and draw
            self.event()
            self.draw()

        self.stop()


# The next two classes handle reponses via keyboard or saccades
class FlashTrialSaccade(FlashTrial):
    """
    FlashTrial on which participants respond by eye movements

    Currently, can only handle TWO flashers / choice options!
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashTrialSaccade, self).__init__(ID, block_trial_ID=block_trial_ID, parameters=parameters,
                                                phase_durations=phase_durations,
                                                session=session, screen=screen, tracker=tracker)

        self.correct_direction = parameters['correct_answer']
        self.directions_verbose = ['left saccade', 'right saccade']
        self.eye_movement_detected_in_phase = False

    def event(self):
        """ Checks for saccades as answers and keyboard responses for escape / scanner pulse """

        if not self.eye_movement_detected_in_phase:
            # Get eye position
            eyepos = self.session.eye_pos()
            eyepos_time = self.session.clock.getTime()

            # Calculate distance travelled in cm
            # distance_from_center = np.sqrt((eyepos[0]-self.session.screen_pix_size[0]/2)**2 +
            #                                (eyepos[1]-self.session.screen_pix_size[1]/2)**2) / \
            #                        self.session.pixels_per_centimeter

            distance_from_center = np.divide(np.sqrt(eyepos[0]**2 + eyepos[1]**2), self.session.pixels_per_centimeter)

            if distance_from_center >= self.session.eye_travel_threshold:
                self.eye_movement_detected_in_phase = True

                # Is the final xpos left or right from center?  left = 0, right = 1
                # ToDO: checkout how eye positions are returned: is screen center (0,0) or n_pix/2?
#                saccade_direction = 0 if eyepos[0] < self.session.screen_pix_size[0]/2 else 1
                saccade_direction = 0 if eyepos[0] < 0 else 1
                saccade_direction_verbose = self.directions_verbose[saccade_direction]

                if self.phase == 1:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during fixation cross 1'])

                elif self.phase == 2:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during cue'])

                elif self.phase == 3:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during fixation cross 2'])

                elif self.phase == 4:
                    self.response = saccade_direction_verbose

                    # Check for early response
                    if (eyepos_time - self.fix2_time) < 0.150:  # (seconds)
                        self.response_type = 3

                        if saccade_direction == self.correct_direction:
                            self.events.append([saccade_direction_verbose, eyepos_time, 'too fast response', 'correct'])
                        else:
                            self.events.append([saccade_direction_verbose, eyepos_time, 'too fast response',
                                                'incorrect'])
                    else:
                        if saccade_direction == self.correct_direction:
                            self.response_type = 1
                            self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade',
                                                'correct'])
                        else:
                            self.response_type = 2
                            self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade',
                                                'incorrect'])

                    self.phase_forward()  # End stimulus presentation when saccade is detected (this will be removed)

                elif self.phase == 5:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during post-stimulus fill time'])  #
                    # This will probably always be detected: drift correction?

                elif self.phase == 6:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during feedback'])  # This will
                    # probably always be detected: drift correction?

                elif self.phase == 7:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during ITI'])  # This will
                    # probably always be detected: drift correction?

        # Don't forget to check keyboard responses for kill signals and/or scanner pulses!
        for i, (ev, ev_time) in enumerate(event.getKeys(timeStamped=self.session.clock)):

            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, ev_time, 'escape: user killed session'])
                    self.stopped = True
                    self.session.stopped = True
                    print('Session stopped!')

                elif ev == 'space':
                    self.events.append([-99, ev_time - self.start_time])
                    self.stopped = True
                    print('Trial canceled by user')

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])

                    if self.phase == 0:
                        self.phase_forward()

    def phase_forward(self):
        """ Do everything the superclass does, but also reset current phase eye movement detection """
        super(FlashTrialSaccade, self).phase_forward()
        self.eye_movement_detected_in_phase = False


class FlashTrialKeyboard(FlashTrial):
    """
    FlashTrial on which participants respond with a keypress
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
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

                elif ev == 'space':
                    self.events.append([-99, ev_time - self.start_time])
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

                            if self.response_time < 0.150:
                                self.response_type = 3  # Too early

                                if ev == self.correct_key:
                                    self.events.append([ev, ev_time, 'too fast response', 'correct',
                                                        self.response_time])
                                else:
                                    self.events.append([ev, ev_time, 'too fast response', 'incorrect',
                                                        self.response_time])
                            else:
                                if ev == self.correct_key:
                                    self.events.append([ev, ev_time, 'first keypress', 'correct',
                                                        self.response_time])
                                    self.response_type = 1
                                else:
                                    self.events.append([ev, ev_time, 'first keypress', 'incorrect',
                                                        self.response_time])
                                    self.response_type = 2
                            self.phase_forward()  # End stimulus presentation upon keypress
                        else:
                            self.events.append([ev, ev_time, 'late keypress (during stimulus)'])

                    elif self.phase == 5:
                        self.events.append([ev, ev_time, 'late keypress (during post-stimulus fill time)'])

                    elif self.phase == 6:
                        self.events.append([ev, ev_time, 'late keypress (during feedback)'])

                    elif self.phase == 7:
                        self.events.append([ev, ev_time, 'late keypress (during ITI)'])

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])

                    if self.phase == 0:
                        self.phase_forward()
