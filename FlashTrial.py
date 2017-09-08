from exp_tools import Trial
from psychopy import visual, event, core
from FlashStim import FlashStim
import numpy as np


class FlashTrial(Trial):
    """ Class that holds the draw() and run() methods for a FlashTrial.

    The event() method determines the response type (manual keypress vs saccadic), and is constructed in a subclass (
    see below).
    """

    def __init__(self, ID, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashTrial, self).__init__(parameters=parameters, phase_durations=phase_durations, session=session,
                                         screen=screen, tracker=tracker)
        self.ID = ID
        self.frame_n = -1
        self.response = None

        self.response_type = 0   # 0 = too late, 1 = correct, 2 = incorrect response

        # Initialize flashing circles objects
        self.stimulus = FlashStim(screen=self.screen, n_flashers=parameters['n_flashers'],
                                  flasher_size=parameters['flasher_size'], positions=parameters['positions'],
                                  trial_evidence_arrays=parameters['trial_evidence_arrays'])

        # Set times
        self.run_time = 0.0
        self.t_time = self.fix_time = self.stimulus_time = self.post_stimulus_time = self.response_time = 0.0

    def draw(self):
        """ Draws the current frame """

        if self.phase == 0:
            self.session.fixation_cross.draw()
        elif self.phase == 1:
            self.stimulus.draw(frame_n=self.frame_n)
        elif self.phase == 2:
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

            # Fixation cross
            if self.phase == 0:
                self.fix_time = self.session.clock.getTime()
                if (self.fix_time - self.start_time) > self.phase_durations[0]:
                    self.phase_forward()

            # # In phase 2, we wait for the scanner pulse (t)
            # if self.phase == 2:
            #     self.t_time = self.session.clock.getTime()
            #     if self.session.scanner == 'n':
            #         # self.pulse_id = np.random.randint(5)+1
            #         self.phase_forward()

            # In phase 2, the stimulus is presented
            if self.phase == 1:
                self.stimulus_time = self.session.clock.getTime()
                if (self.stimulus_time - self.phase_time) > self.phase_durations[1]:
                    self.phase_forward()

            # Phase 3 reflects the ITI
            if self.phase == 2:
                self.feedback_time = self.session.clock.getTime()
                if (self.feedback_time - self.stimulus_time) > self.phase_durations[2]:
                    self.stopped = True

            if self.phase == 3:
                self.post_stimulus_time = self.session.clock.getTime()
                if (self.post_stimulus_time - self.stimulus_time) > self.phase_durations[2]:
                    self.stopped = True

            # events and draw
            self.event()
            self.draw()

        self.stop()


class FlashTrialSaccade(FlashTrial):
    """
    FlashTrial on which participants respond by eye movements

    Currently, can only handle TWO flashers / choice options!
    """

    def __init__(self, ID, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashTrialSaccade, self).__init__(ID, parameters=parameters, phase_durations=phase_durations,
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
                saccade_direction = 0 if eyepos[0] < self.session.screen_pix_size[0]/2 else 1
                saccade_direction_verbose = self.directions_verbose[saccade_direction]

                if self.phase == 0:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during fixation cross'])

                elif self.phase == 1:
                    if saccade_direction == self.correct_direction:
                        self.response_type = 1
                        self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade', 'correct'])
                    else:
                        self.response_type = 2
                        self.events.append([saccade_direction_verbose, eyepos_time, 'response saccade', 'incorrect'])
                    self.phase_forward()  # End stimulus presentation when saccade is detected

                elif self.phase == 2:
                    self.events.append([saccade_direction_verbose, eyepos_time, 'during feedback'])  # This will
                    # probably always be detected: drift correction?

                elif self.phase == 3:
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

    def phase_forward(self):
        """ Do everything the superclass does, but also reset current phase eye movement detection """
        super(FlashTrialSaccade, self).phase_forward()
        self.eye_movement_detected_in_phase = False


class FlashTrialKeyboard(FlashTrial):
    """
    FlashTrial on which participants respond with a keypress
    """

    def __init__(self, ID, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashTrialKeyboard, self).__init__(ID, parameters=parameters, phase_durations=phase_durations,
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

                    if self.phase == 0:
                        self.events.append([ev, ev_time, 'early keypress'])

                    elif self.phase == 1:
                        self.response = ev

                        if i == 0:  # First keypress
                            self.response_time = ev_time - self.phase_time

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

                    elif self.phase == 2:
                        self.events.append([ev, ev_time, 'late keypress (during feedback)'])

                    elif self.phase == 3:
                        self.events.append([ev, ev_time, 'late keypress (during ITI)'])

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])
