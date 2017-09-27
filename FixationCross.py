from psychopy import visual


class FixationCross(object):

    def __init__(self, win, rad, bg):

        self.fixation_circle = visual.Circle(win, radius=rad, units='deg', fillColor='black', lineColor=bg)
        self.fixation_vertical_bar = visual.Rect(win, width=0.2, height=rad * 2, units='deg', fillColor=bg,
                                                 lineColor=bg)
        self.fixation_horizontal_bar = visual.Rect(win, width=rad * 2, height=0.2, units='deg', fillColor=bg,
                                                 lineColor=bg)
        self.fixation_bulls = visual.Circle(win, radius=0.1, units='deg', fillColor='black', lineColor='black')

    def draw(self):

        self.fixation_circle.draw()
        self.fixation_vertical_bar.draw()
        self.fixation_horizontal_bar.draw()
        self.fixation_bulls.draw()