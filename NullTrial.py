from exp_tools import Trial
from psychopy import event


class NullTrial(Trial):
    """ Class runs a NullTrial. NullTrials only show the fixation cross,
    and optionally, also crosses on the left and right of the screen (for saccadic responses). Scanner pulses are
    recorded.

    Assumes that the actual visual objects (arrows, crosses, feedback texts) are initiated in the Session. This greatly
    improves speed, because rendering is done at the start of the experiment rather than at the start of the trial.

    Parameters
    ----------
    ID: int
        ID number of trial
    block_trial_ID: int
        Number of trial within the current block
    parameters: dict
        Dictionary containing parameters that specify what is drawn. Currently, only supports "draw_crosses" as a
        key, with boolean value.
    phase_durations : list
        List specifying the durations of each phase of the NullTrial
    session: exp_tools.Session instance
    screen: psychopy.visual.Window instance
    tracker: pygaze.EyeTracker object
        Passed on to parent class
    """

    def __init__(self, ID, block_trial_ID=0, parameters={}, phase_durations=[], session=None, screen=None,
                 tracker=None):
        super(NullTrial, self).__init__(parameters=parameters, phase_durations=phase_durations, session=session,
                                        screen=screen, tracker=tracker)
        self.ID = ID
        self.frame_n = -1
        self.response = None
        self.block_trial_ID = block_trial_ID
        self.draw_crosses = parameters['draw_crosses']

        self.n_TRs = 0

        # Initialize times  -> what timing here?
        self.run_time = 0.0
        self.t_time = self.fix1_time = self.cue_time = self.fix2_time = self.stimulus_time = self.post_stimulus_time = \
          self.feedback_time = self.ITI_time = 0.0

    def draw(self):
        """ Draws whatever should be drawn (fixation cross and maybe target crosses) """

        if self.draw_crosses:
            self.session.crosses[0].draw()
            self.session.crosses[1].draw()

        self.session.fixation_cross.draw()

        super(NullTrial, self).draw()

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
                    self.n_TRs += 1

                    if self.phase == 0:
                        self.phase_forward()

    def run(self):
        """ Everything here is directly copied from the FlashTrial. We act as if the normal 'phases' are being run, but
        instead show a fixation cross (and maybe target crosses left/right), only check for events (pulses and stop
        keys)
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
                    self.phase_forward()

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

            # events and draw, but only if we haven't stopped yet
            if not self.stopped:
                self.event()
                self.draw()

        self.stop()
