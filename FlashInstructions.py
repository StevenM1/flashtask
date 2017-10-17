#!/usr/bin/env python
# encoding: utf-8
from exp_tools import Trial
from psychopy import visual, event


class FlashInstructions(Trial):

    def __init__(self, ID, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashInstructions, self).__init__(parameters=parameters, phase_durations=phase_durations,
                                                session=session, screen=screen, tracker=tracker)

        self.ID = ID
        self.phase_durations = phase_durations
        self.start_time = self.end_time = 0

    def draw(self):

        self.session.current_instruction.draw()
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

        self.start_time = self.session.clock.getTime()

        while not self.stopped:
            self.end_time = self.session.clock.getTime()
            if self.end_time - self.start_time >= self.phase_durations[0]:
                self.stopped = True

            # check for keyboard (events) and draw
            if not self.stopped:
                self.event()
                self.draw()

        self.stop()


class FlashInstructionsPractice(FlashInstructions):
    """
    Same as FlashInstructions, but allows moving between blocks
    """

    def __init__(self, ID, parameters={}, phase_durations=[], session=None, screen=None, tracker=None):
        super(FlashInstructionsPractice, self).__init__(ID=ID, parameters=parameters,
                                                           phase_durations=phase_durations, session=session,
                                                           screen=screen, tracker=tracker)

    def event(self):
        """
        Only listen for space (skip instructions), escape (kill session), and scanner pulses
        """

        for i, (ev, ev_time) in enumerate(event.getKeys(timeStamped=self.session.clock)):
            # ev_time is the event timestamp relative to the Session Clock

            if len(ev) > 0:
                print(ev)
                if ev in ['esc', 'escape']:
                    self.events.append([-99, ev_time, 'escape: user killed session'])
                    self.stopped = True
                    self.session.stopped = True
                    print('Session stopped!')

                elif ev == 'space':
                    self.events.append([0, ev_time - self.start_time])
                    self.session.stop_instructions = False
                    self.stopped = True

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, ev_time, 'pulse'])

                elif ev == 'left':
                    if not self.session.current_block == 0:
                        self.events.append([-1, ev_time, 'user restarts previous block'])
                        self.session.current_block -= 1
                        self.stopped = True
                        self.session.stop_instructions = True

                elif ev == 'right':
                    if not self.session.current_block == 7:
                        self.events.append([-2, ev_time, 'user fast forwards to next block'])
                        self.session.current_block += 1
                        self.stopped = True
                        self.session.stop_instructions = True