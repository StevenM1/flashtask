from psychopy import visual


class FlashStim(object):

    def __init__(self, screen, n_flashers, positions, flasher_size, trial_evidence_arrays):
        self.screen = screen
        self.n_flashers = n_flashers
        self.trial_evidence_arrays = trial_evidence_arrays

        self.flasher_objects = []
        for i in range(self.n_flashers):
            self.flasher_objects.append(visual.Circle(win=self.screen, name='flasher_'+str(i),
                                                      size=[flasher_size, flasher_size], ori=0,
                                                      pos=positions, lineWidth=0, lineColor=[0, 0, 0],
                                                      lineColorSpace='rgb', fillColor=[1, 1, 1], fillColorSpace='rgb',
                                                      opacity=1, depth=-1.0, interpolate=True))

    def draw(self, frame_n):

        for i in range(self.n_flashers):
            self.flasher_objects[i].opacity = self.trial_evidence_arrays[i][frame_n]
            self.flasher_objects[i].draw()
