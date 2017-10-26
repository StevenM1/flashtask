from psychopy import visual


class FixationCross(object):
    """
    Fixation cross built according to recommendations in the following paper:

    Thaler, L., Schutz, A.C., Goodale, M.A., & Gegenfurtner, K.R. (2013). What is the best fixation target? The
    effect of target shape on stability of fixational eye movements. Vision research (2016), 76, 31-42.

    This small fixation cross combining a cross, bulls eye, and circle, apparently minimizes micro-saccadic movements
    during fixation.

    Parameters
    -----------
    win : psychopy.visual.Window instance
    outer_radius : float
        Radius of outer circle, in degrees of visual angle. Defaults to 0.15
    inner_radius : float
        Radius of inner circle (bulls eye), in degrees of visual angle. Defaults to 0.3
    bg : tuple
        RGB of background color. Defaults to (0.5, 0.5, 0.5) - gray screen.
    """


    def __init__(self, win, outer_radius=.3, inner_radius=.15, bg=(0.5, 0.5, 0.5)):

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
        """
        Draws the fixation cross
        """

        self.fixation_circle.draw()
        self.fixation_vertical_bar.draw()
        self.fixation_horizontal_bar.draw()
        self.fixation_bulls.draw()