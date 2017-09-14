#!/usr/bin/env python
# encoding: utf-8
from exp_tools import Trial
from psychopy import visual, event


class FlashInstructions(Trial):

    def __init__(self, ID, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashInstructions, self).__init__(parameters=parameters, phase_durations=phase_durations,
                                                session=session, screen=screen, tracker=tracker)

        self.ID = ID
        self.create_stimuli()

    def create_stimuli(self):
        # Initialize instructions
        this_instruction_string = 'Decide which circle flashes most often'
        self.instruction = visual.TextStim(self.screen, text=this_instruction_string, font='Helvetica Neue', pos=(0, 0),
                                           italic=True, height=30, alignHoriz='center', units='pix')
        self.instruction.setSize((1200, 50))

    def draw(self):

        self.instruction.draw()
        super(FlashInstructions, self).draw()

    def event(self):
        """
        Only listen for space (skip instructions), escape (kill session), and scanner pulses
        """

        for i, (ev, ev_time) in enumerate(event.getKeys(timeStamped=self.session.clock)):
            # ev_time is the event timestamp relative to the Session Clock

            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, ev_time, 'escape: user killed session'])
                    self.stopped = True
                    self.session.stopped = True
                    print('Session stopped!')

                elif ev == 'space':
                    self.events.append([0, ev_time - self.start_time])
                    self.stopped = True

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])

    def run(self):
        super(FlashInstructions, self).run()

        while not self.stopped:
            # check for keyboard (events) and draw
            self.event()
            self.draw()

        self.stop()
