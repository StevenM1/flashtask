from psychopy import visual


class FixationCross(object):

    def __init__(self, win, outer_radius, inner_radius, bg):

        self.fixation_circle = visual.Circle(win,
                                             radius=outer_radius,
                                             units='deg', fillColor='black', lineColor=bg)
        self.fixation_vertical_bar = visual.Rect(win, width=inner_radius, height=outer_radius * 2,
                                                 units='deg', fillColor=bg,
                                                 lineColor=bg)
        self.fixation_horizontal_bar = visual.Rect(win, width=outer_radius * 2, height=inner_radius,
                                                   units='deg', fillColor=bg,
                                                   lineColor=bg)
        self.fixation_bulls = visual.Circle(win, radius=inner_radius/2,
                                            units='deg', fillColor='black',
                                            lineColor='black')

    def draw(self):

        self.fixation_circle.draw()
        self.fixation_vertical_bar.draw()
        self.fixation_horizontal_bar.draw()
        self.fixation_bulls.draw()