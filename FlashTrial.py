from exp_tools import Trial
from psychopy import visual, event
from FlashStim import FlashStim


class FlashTrial(Trial):

    def __init__(self, ID, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashTrial, self).__init__(parameters=parameters, phase_durations=phase_durations, session=session,
                                         screen=screen, tracker=tracker)
        self.ID = ID
        self.frame_n = -1
        self.response = None
        self.response_type = 0   # 0 = too late, 1 = correct, 2 = incorrect response
        self.correct_key = parameters['correct_key']
        self.incorrect_keys = parameters['incorrect_keys']

        self.stimulus = FlashStim(screen=self.screen, n_flashers=parameters['n_flashers'],
                                  flasher_size=parameters['flasher_size'], positions=parameters['positions'],
                                  trial_evidence_arrays=parameters['trial_evidence_arrays'])

        this_instruction_string = 'Decide which circle flashes most often'
        self.instruction = visual.TextStim(self.screen, text=this_instruction_string, font='Helvetica Neue', pos=(0, 0),
                                           italic=True, height=30, alignHoriz='center', units='pix')
        self.instruction.setSize((1200, 50))

        self.run_time = 0.0
        self.instruct_time = self.t_time = self.fix_time = self.stimulus_time = self.post_stimulus_time = \
            self.response_time = 0.0

    def draw(self):

        if self.phase == 0:
            if self.ID == 0:
                self.instruction.draw()
            else:
                self.phase_forward()
        if self.phase == 1:
            self.session.fixation_cross.draw()
        elif self.phase == 2:
            self.stimulus.draw(frame_n=self.frame_n)
        elif self.phase == 3:
            self.session.feedback_text_objects[self.response_type].draw()
        super(FlashTrial, self).draw()

    def event(self):

        for i, (ev, ev_time) in enumerate(event.getKeys(timeStamped=True)):
            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, ev_time, 'escape: user killed session'])
                    self.stopped = True
                    self.session.stopped = True
                    print('Session stopped!')

                elif ev == 'space':
                    self.events.append([0, ev_time - self.start_time])
                    if self.phase == 0:
                        self.phase_forward()
                    else:
                        self.events.append([-99, ev_time - self.start_time])
                        self.stopped = True
                        print('Trial canceled by user')

                elif ev in self.session.response_keys:

                    if self.phase == 1:
                        self.events.append([ev, ev_time, 'early keypress'])

                    elif self.phase == 2:
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

                    elif self.phase == 3:
                        self.events.append([ev, ev_time, 'late keypress (during feedback)'])

                    elif self.phase == 4:
                        self.events.append([ev, ev_time, 'late keypress (during ITI)'])

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])

    def phase_forward(self):
        """ Call the superclass phase_forward method first, and reset the current frame number to 0 """
        super(FlashTrial, self).phase_forward()
        self.frame_n = 0

    def run(self):
        super(FlashTrial, self).run()

        while not self.stopped:
            self.frame_n += 1
            self.run_time = self.session.clock.getTime() - self.start_time

            # Only in trial 1, phase 0 represents the instruction period.
            # After the first trial, this phase is skipped immediately
            if self.phase == 0:
                self.instruct_time = self.session.clock.getTime()

                if self.ID != 0:
                    self.phase_forward()

            # Fixation cross
            if self.phase == 1:
                self.fix_time = self.session.clock.getTime()
                if (self.fix_time - self.instruct_time) > self.phase_durations[1]:
                    self.phase_forward()

            # # In phase 2, we wait for the scanner pulse (t)
            # if self.phase == 2:
            #     self.t_time = self.session.clock.getTime()
            #     if self.session.scanner == 'n':
            #         # self.pulse_id = np.random.randint(5)+1
            #         self.phase_forward()

            # In phase 2, the stimulus is presented
            if self.phase == 2:
                self.stimulus_time = self.session.clock.getTime()
                if (self.stimulus_time - self.phase_time) > self.phase_durations[2]:
                    self.phase_forward()

            # Phase 3 reflects the ITI
            if self.phase == 3:
                self.post_stimulus_time = self.session.clock.getTime()
                if (self.post_stimulus_time - self.stimulus_time) > self.phase_durations[3]:
                    self.stopped = True

            # events and draw
            self.event()
            self.draw()

        self.stop()

