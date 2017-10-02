from exp_tools import Trial
from psychopy import event


class NullTrial(Trial):
    """ Class that holds the draw() and run() methods for a LocalizerTrial.

    The event() method determines the response type (manual keypress vs saccadic), and is constructed in a subclass (
    see below).
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None,
                 tracker=None):
        super(NullTrial, self).__init__(parameters=parameters, phase_durations=phase_durations, session=session,
                                        screen=screen, tracker=tracker)
        self.ID = ID
        self.frame_n = -1
        self.response = None
        self.block_trial_ID = block_trial_ID

        # Initialize times  -> what timing here?
        self.run_time = 0.0
        self.t_time = self.fix1_time = self.cue_time = self.fix2_time = self.stimulus_time = self.post_stimulus_time = \
          self.feedback_time = self.ITI_time = 0.0

    def event(self):
        """ Checks for keyboard responses and scanner pulses """

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

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])

                    if self.phase == 0:
                        self.phase_forward()

    def run(self):
        """ Everything here is directly copied from the FlashTrial. We act as if the normal 'phases' are being run, but
        instead show nothing, only check for events (pulses and stop keys)
        """

        super(NullTrial, self).run()

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
                    self.stopped = True

            # events and draw, but only if we haven't stopped yet
            if not self.stopped:
                self.event()
                self.draw()

        self.stop()