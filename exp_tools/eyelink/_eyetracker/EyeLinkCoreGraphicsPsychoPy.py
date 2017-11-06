# Copyright (C) 2016 Zhiguo Wang
# Copyright (C) 2017 SR Research
# Distributed under the terms of the GNU General Public License (GPL).

from psychopy import visual, monitors, event, core, sound
from numpy import linspace
from math import sin, cos, pi
from PIL import Image
import array, string, pylink, psychopy, pygaze
from pygaze import settings
from pygaze.screen import Screen

class EyeLinkCoreGraphicsPsychoPy(pylink.EyeLinkCustomDisplay):
    def __init__(self, libeyelink, win, tracker):#
        '''Initialize a Custom EyeLinkCoreGraphics  
        
        tracker: an eye-tracker instance
        win: the Psychopy display we plan to use for stimulus presentation  '''
        
        pylink.EyeLinkCustomDisplay.__init__(self)
        self.display = win  # SM: get the PsychoPy.window instance
        self.libeyelink = libeyelink
#        win = self.display
        # Let's disable the beeps as the Psychopy "sound" module will bite our ass
        #self.__target_beep__ = sound.Sound('type.wav')
        #self.__target_beep__done__ = sound.Sound('qbeep.wav')
        #self.__target_beep__error__ = sound.Sound('error.wav')
        self.imgBuffInitType = 'I'
        self.imagebuffer = array.array(self.imgBuffInitType)
        self.pal = None	
        self.size = (384,320)
        self.bg_color = win.color
        self.sizeX = win.size[0]
        self.sizeY = win.size[1]
      
        # check the screen units of Psychopy and make all necessary conversions for the drawing functions
        self.units = win.units
        self.monWidthCm  = win.monitor.getWidth()
        self.monViewDist = win.monitor.getDistance()
        self.monSizePix  = win.monitor.getSizePix()
                
        # a scaling factor to make the screen units right for Psychopy
        self.cfX = 1.0 
        self.cfY = 1.0
        if self.units == 'pix': 
            pass 
        elif self.units == 'height':
            self.cfX = 1.0/self.monSizePix[1]
            self.cfY = 1.0/self.monSizePix[1]
        elif self.units == 'norm':
            self.cfX = 2.0/self.monSizePix[0]
            self.cfY = 2.0/self.monSizePix[1]
        elif self.units == 'cm':
            self.cfX = self.monWidthCm*1.0/self.monSizePix[0]
            self.cfY = self.cfX         
        else: # here comes the 'deg*' units
            self.cfX = self.monWidthCm/self.monViewDist/pi*180.0/self.monSizePix[0]
            self.cfY = self.cfX
            
        # initial setup for the mouse
        self.display.mouseVisible = False
        self.mouse = event.Mouse(visible=False)
        self.mouse.setPos([0,0]) # make the mouse appear at the center of the camera image
        self.last_mouse_state = -1

        # image title
        self.msgHeight = self.size[1]/20.0*self.cfY
        self.title = visual.TextStim(self.display,'', height=self.msgHeight, color=[1,1,1])
        
        # lines
        self.line = visual.Line(self.display, start=(0, 0), end=(0,0),
                           lineWidth=2.0*self.cfX, lineColor=[0,0,0])

        # Stolen from PyGaze
        self.esc_pressed = None
        self.display_open = True

        print('Is this not run then?')
        self.xc = self.libeyelink.display.dispsize[0] / 2
        self.yc = self.libeyelink.display.dispsize[1] / 2
        self.extra_info = True
        self.ld = 40  # line distance
        self.fontsize = libeyelink.fontsize
        self.title = ""

        self.draw_menu_screen()

    def draw_menu_screen(self):
        """ Draws menu screen """
        #
        #
        # title = visual.TextStim(text="Eyelink calibration menu",
        #                         pos=(self.xc, self.yc - 6 * self.ld), font='mono',
        #                         height=int(2 * self.fontsize), antialias=True)
        #
        # vers = visual.TextStim(text="%s (pygaze %s, pylink %s)" \
        #                                % (self.libeyelink.eyelink_model, pygaze.version,
        #                                   pylink.__version__), pos=(self.xc, self.yc - 5 * self.ld),
        #                        font='mono', height=int(.8 * self.fontsize), antialias=True)
        #
        # cal = visual.TextStim(text="Press C to calibrate",
        #                       pos=(self.xc, self.yc - 3 * self.ld), font='mono',
        #                       height=self.fontsize, antialias=True)
        #
        # val = visual.TextStim(text="Press V to validate",
        #                       pos=(self.xc, self.yc - 2 * self.ld), font='mono',
        #                       height=self.fontsize, antialias=True)
        #
        # autothres = visual.TextStim(text="Press A to auto-threshold",
        #                             pos=(self.xc, self.yc - 1 * self.ld), font='mono',
        #                             height=self.fontsize, antialias=True)
        #
        # extra_info = visual.TextStim(text="Press I to toggle extra info in camera image",
        #                              pos=(self.xc, self.yc - 0 * self.ld), font='mono',
        #                              height=self.fontsize, antialias=True)
        #
        # cam = visual.TextStim(text="Press Enter to show camera image",
        #                       pos=(self.xc, self.yc + 1 * self.ld), font='mono',
        #                       height=self.fontsize, antialias=True)
        #
        # arrow_keys = visual.TextStim(text="(then change between images using the arrow keys)",
        #     pos=(self.xc, self.yc + 2 * self.ld), font='mono',
        #     height=self.fontsize, antialias=True)
        #
        # abort = visual.TextStim(text="Press Escape to abort experiment",
        #                         pos=(self.xc, self.yc + 4 * self.ld), font='mono',
        #                         height=self.fontsize, antialias=True)
        #
        # exit = visual.TextStim(text="Press Q to exit menu",
        #                        pos=(self.xc, self.yc + 5 * self.ld), font='mono',
        #                        height=self.fontsize, antialias=True)
        #
        # self.menuscreen = [title, vers, cal, val, autothres, extra_info, cam, arrow_keys, abort, exit]

        self.menuscreen = Screen(disptype=settings.DISPTYPE, mousevisible=False)
        self.menuscreen.draw_text(text="Eyelink calibration menu",
                                  pos=(self.xc, self.yc - 6 * self.ld), center=True, font='mono',
                                  fontsize=int(2 * self.fontsize), antialias=True)
        self.menuscreen.draw_text(text="%s (pygaze %s, pylink %s)" \
                                       % (self.libeyelink.eyelink_model, pygaze.version,
                                          pylink.__version__), pos=(self.xc, self.yc - 5 * self.ld), center=True,
                                  font='mono', fontsize=int(.8 * self.fontsize), antialias=True)
        self.menuscreen.draw_text(text="Press C to calibrate",
                                  pos=(self.xc, self.yc - 3 * self.ld), center=True, font='mono',
                                  fontsize=self.fontsize, antialias=True)
        self.menuscreen.draw_text(text="Press V to validate",
                                  pos=(self.xc, self.yc - 2 * self.ld), center=True, font='mono',
                                  fontsize=self.fontsize, antialias=True)
        self.menuscreen.draw_text(text="Press A to auto-threshold",
                                  pos=(self.xc, self.yc - 1 * self.ld), center=True, font='mono',
                                  fontsize=self.fontsize, antialias=True)
        self.menuscreen.draw_text(text="Press I to toggle extra info in camera image",
                                  pos=(self.xc, self.yc - 0 * self.ld), center=True, font='mono',
                                  fontsize=self.fontsize, antialias=True)
        self.menuscreen.draw_text(text="Press Enter to show camera image",
                                  pos=(self.xc, self.yc + 1 * self.ld), center=True, font='mono',
                                  fontsize=self.fontsize, antialias=True)
        self.menuscreen.draw_text(
            text="(then change between images using the arrow keys)",
            pos=(self.xc, self.yc + 2 * self.ld), center=True, font='mono',
            fontsize=self.fontsize, antialias=True)
        self.menuscreen.draw_text(text="Press Escape to abort experiment",
                                  pos=(self.xc, self.yc + 4 * self.ld), center=True, font='mono',
                                  fontsize=self.fontsize, antialias=True)
        self.menuscreen.draw_text(text="Press Q to exit menu",
                                  pos=(self.xc, self.yc + 5 * self.ld), center=True, font='mono',
                                  fontsize=self.fontsize, antialias=True)

    def close(self):
        self.display_open = False

    def setTracker(self, tracker):
        ''' set proper tracker parameters '''
        
        self.tracker = tracker
        self.tracker_version = tracker.getTrackerVersion()
        if self.tracker_version >=3:
            self.tracker.sendCommand("enable_search_limits=YES")
            self.tracker.sendCommand("track_search_limits=YES")
            self.tracker.sendCommand("autothreshold_click=YES")
            self.tracker.sendCommand("autothreshold_repeat=YES")
            self.tracker.sendCommand("enable_camera_position_detect=YES")
 
    def setup_cal_display(self):
        '''Set up the calibration display before entering the calibration/validation routine'''
        
        # self.display.color = self.bg_color
        # self.title.autoDraw = False
        # for menu_screen_item in self.menuscreen:
        #     menu_screen_item.setAutoDraw(True)
        # self.display.flip()

        # show instructions
        self.libeyelink.display.fill(self.menuscreen)
        self.libeyelink.display.show()

    def clear_cal_display(self):
        '''Clear the calibration display'''

        # for menu_screen_item in self.menuscreen:
        #     menu_screen_item.setAutoDraw(False)
        self.libeyelink.display.fill()

        self.libeyelink.display.show()
        self.display.color = self.bg_color
        
    def exit_cal_display(self):
        '''Exit the calibration/validation routine'''
        
        self.clear_cal_display()

    def record_abort_hide(self):
        '''This function is called if aborted'''
        
        pass

    def erase_cal_target(self):
        '''Erase the calibration/validation & drift-check target'''
        
        self.display.color = self.bg_color
        self.display.flip()

    def draw_cal_target(self, x, y):#
        '''Draw the calibration/validation & drift-check  target'''
        
        xVis = (x - self.sizeX/2)*self.cfX
        yVis = (self.sizeY/2 - y)*self.cfY
        cal_target_out = visual.GratingStim(self.display, tex='none', mask='circle', size=2.0/100*self.sizeX*self.cfX, color=[1.0,1.0,1.0])
        cal_target_in  = visual.GratingStim(self.display, tex='none', mask='circle', size=2.0/300*self.sizeX*self.cfX, color=[-1.0,-1.0,-1.0])
        cal_target_out.setPos((xVis, yVis))
        cal_target_in.setPos((xVis, yVis))
        cal_target_out.draw()
        cal_target_in.draw()
        self.display.flip()

    def play_beep(self, beepid):
        ''' Play a sound during calibration/drift correct.'''

        # pass
        # we need to disable the beeps to make this library work on all platforms
        #if beepid == pylink.CAL_TARG_BEEP or beepid == pylink.DC_TARG_BEEP:
        #    self.__target_beep__.play()
        #if beepid == pylink.CAL_ERR_BEEP or beepid == pylink.DC_ERR_BEEP:
        #    self.__target_beep__error__.play()
        #if beepid in [pylink.CAL_GOOD_BEEP, pylink.DC_GOOD_BEEP]:
        #    self.__target_beep__done__.play()

        if beepid == pylink.CAL_TARG_BEEP:
            # For some reason, playing the beep here doesn't work, so we have
            # to play it when the calibration target is drawn.
            if settings.EYELINKCALBEEP:
                self.__target_beep__.play()
        elif beepid == pylink.CAL_ERR_BEEP or beepid == pylink.DC_ERR_BEEP:
            # show a picture
            self.screen.clear()
            self.screen.draw_text(
                text="calibration lost, press 'Enter' to return to menu",
                pos=(self.xc, self.yc), center=True, font='mono',
                fontsize=self.fontsize, antialias=True)
            self.display.fill(self.screen)
            self.display.show()
            # play beep
            if settings.EYELINKCALBEEP:
                self.__target_beep__error__.play()
        elif beepid == pylink.CAL_GOOD_BEEP:
            self.screen.clear()
            if self.state == "calibration":
                self.screen.draw_text(
                    text="Calibration succesfull, press 'v' to validate",
                    pos=(self.xc, self.yc), center=True, font='mono',
                    fontsize=self.fontsize, antialias=True)
            elif self.state == "validation":
                self.screen.draw_text(
                    text="Validation succesfull, press 'Enter' to return to menu",
                    pos=(self.xc, self.yc), center=True, font='mono',
                    fontsize=self.fontsize, antialias=True)
            else:
                self.screen.draw_text(text="Press 'Enter' to return to menu",
                                      pos=(self.xc, self.yc), center=True, font='mono',
                                      fontsize=self.fontsize, antialias=True)
            # show screen
            self.display.fill(self.screen)
            self.display.show()
            # play beep
            if settings.EYELINKCALBEEP:
                self.__target_beep__done__.play()
        else:  # DC_GOOD_BEEP	or DC_TARG_BEEP
            pass

    def getColorFromIndex(self, colorindex):
         '''Return psychopy colors for elements in the camera image'''
         
         if colorindex   ==  pylink.CR_HAIR_COLOR:          return (1, 1, 1)
         elif colorindex ==  pylink.PUPIL_HAIR_COLOR:       return (1, 1, 1)
         elif colorindex ==  pylink.PUPIL_BOX_COLOR:        return (-1, 1, -1)
         elif colorindex ==  pylink.SEARCH_LIMIT_BOX_COLOR: return (1, -1, -1)
         elif colorindex ==  pylink.MOUSE_CURSOR_COLOR:     return (1, -1, -1)
         else:                                              return (0,0,0)

    def draw_line(self, x1, y1, x2, y2, colorindex):
        '''Draw a line. This is used for drawing crosshairs/squares'''

        y1 = (y1 * -1 + self.size[1]/2)*self.cfY
        x1 = (x1 * 1  - self.size[0]/2)*self.cfX
        y2 = (y2 * -1 + self.size[1]/2)*self.cfY
        x2 = (x2 * 1  - self.size[0]/2)*self.cfX

        color = self.getColorFromIndex(colorindex)
        self.line.start     = (x1, y1)
        self.line.end       = (x2, y2)
        self.line.lineColor = color
        self.line.draw()

    def draw_lozenge(self, x, y, width, height, colorindex):
        ''' draw a lozenge to show the defined search limits'''
        
        y = (y * -1 + self.size[1] - self.size[1]/2)*self.cfY
        x = (x * 1  - self.size[0]/2)*self.cfX
        width = width*self.cfX; height = height*self.cfY
        color = self.getColorFromIndex(colorindex)
        
        if width > height:
            rad = height / 2
            if rad == 0: 
                return #cannot draw the circle with 0 radius
            #draw the lines
            line1 = visual.Line(self.display, lineColor=color, lineWidth=2.0*self.cfX, start=(x + rad, y), end=(x + width - rad, y))
            line2 = visual.Line(self.display, lineColor=color, lineWidth=2.0*self.cfX, start=(x + rad, y - height), end=(x + width - rad, y - height))
            
            #draw semicircles
            Xs1 = [rad*cos(t) + x + rad for t in linspace(pi/2, pi/2+pi, 72)]
            Ys1 = [rad*sin(t) + y - rad for t in linspace(pi/2, pi/2+pi, 72)]

            Xs2 = [rad*cos(t) + x - rad + width for t in linspace(pi/2+pi, pi/2+2*pi, 72)]
            Ys2 = [rad*sin(t) + y - rad for t in linspace(pi/2+pi, pi/2+2*pi, 72)]          
            lozenge1 = visual.ShapeStim(self.display, vertices = zip(Xs1, Ys1), lineWidth=2.0*self.cfX, lineColor=color, closeShape=False)
            lozenge2 = visual.ShapeStim(self.display, vertices = zip(Xs2, Ys2), lineWidth=2.0*self.cfX, lineColor=color, closeShape=False)
        else:
            rad = width / 2

            #draw the lines
            line1 = visual.Line(self.display, lineColor=color, lineWidth=2.0*self.cfX, start=(x, y - rad), end=(x, y - height + rad))
            line2 = visual.Line(self.display, lineColor=color, lineWidth=2.0*self.cfX, start=(x + width, y - rad), end=(x + width, y - height + rad))

            #draw semicircles
            if rad == 0: 
                return #cannot draw sthe circle with 0 radius

            Xs1 = [rad*cos(t) + x + rad for t in linspace(0, pi, 72)]
            Ys1 = [rad*sin(t) + y - rad for t in linspace(0, pi, 72)]

            Xs2 = [rad*cos(t) + x + rad for t in linspace(pi, 2*pi, 72)]
            Ys2 = [rad*sin(t) + y + rad - height for t in linspace(pi, 2*pi, 72)]

            lozenge1 = visual.ShapeStim(self.display, vertices = zip(Xs1, Ys1),lineWidth=2.0*self.cfX, lineColor=color, closeShape=False)
            lozenge2 = visual.ShapeStim(self.display, vertices = zip(Xs2, Ys2),lineWidth=2.0*self.cfX, lineColor=color, closeShape=False)    
        lozenge1.draw()
        lozenge2.draw()
        line1.draw()
        line2.draw()

    def get_mouse_state(self):#
        '''Get the current mouse position and status'''
        
        X, Y = self.mouse.getPos()
        mX = self.size[0]/2 + X*1.0/self.cfX  
        mY = self.size[1]/2 - Y*1.0/self.cfY
        if mX <=0: mX =  0
        if mX > self.size[0]: mX = self.size[0]
        if mY < 0: mY =  0
        if mY > self.size[1]: mY = self.size[1]

        state = self.mouse.getPressed()[0] 
        return ((mX, mY), state)


    def get_input_key(self):
        ''' this function will be constantly pools, update the stimuli here is you need
        dynamic calibration target '''

        if not self.display_open:
            return None

        ky=[]
        for keycode, modifier in event.getKeys(modifiers=True):
            k= pylink.JUNK_KEY
            if keycode   == 'f1': k = pylink.F1_KEY
            elif keycode == 'f2': k = pylink.F2_KEY
            elif keycode == 'f3': k = pylink.F3_KEY
            elif keycode == 'f4': k = pylink.F4_KEY
            elif keycode == 'f5': k = pylink.F5_KEY
            elif keycode == 'f6': k = pylink.F6_KEY
            elif keycode == 'f7': k = pylink.F7_KEY
            elif keycode == 'f8': k = pylink.F8_KEY
            elif keycode == 'f9': k = pylink.F9_KEY
            elif keycode == 'f10': k = pylink.F10_KEY
            elif keycode == 'pageup': k = pylink.PAGE_UP
            elif keycode == 'pagedown': k = pylink.PAGE_DOWN
            elif keycode == 'up': k = pylink.CURS_UP
            elif keycode == 'down': k = pylink.CURS_DOWN
            elif keycode == 'left': k = pylink.CURS_LEFT
            elif keycode == 'right': k = pylink.CURS_RIGHT
            elif keycode == 'backspace': k = ord('\b')
            elif keycode == 'return': k = pylink.ENTER_KEY
            elif keycode == 'space': k = ord(' ')
            elif keycode == 'escape':
                k = 'q'
                self.esc_pressed = True
            elif keycode == 'q':
                k = pylink.ESC_KEY
                self.state = None
            elif keycode == "c":
                k = ord("c")
                self.state = "calibration"
            elif keycode == "v":
                k = ord("v")
                self.state = "validation"
            elif keycode == "a":
                k = ord("a")
            elif keycode == "i":
                self.extra_info = not self.extra_info
                k = 0
            elif keycode == 'tab': k = ord('\t')
            elif keycode in string.ascii_letters: k = ord(keycode)
            elif k== pylink.JUNK_KEY: key = 0

            if modifier['alt']==True: mod = 256
            else: mod = 0
            
            ky.append(pylink.KeyInput(k, mod))
            #event.clearEvents()
        return ky

    def exit_image_display(self):
        '''Clcear the camera image'''
        
        self.clear_cal_display()
        self.display.flip()

    def alert_printf(self,msg):
        '''Print error messages.'''
        
        print "Error: " + msg

    def setup_image_display(self, width, height): 
        ''' set up the camera image, for newer APIs, the size is 384 x 320 pixels'''
        
        self.title.autoDraw = True
        self.last_mouse_state = -1
        self.size = (width, height)

    def image_title(self, text):
        '''Draw title text below the camera image'''
        
        self.title.text = text
        title_pos = (0, 0-self.size[0]/2.0*self.cfY-self.msgHeight)
        self.title.pos = title_pos
        
        
    def draw_image_line(self, width, line, totlines, buff):#
        '''Display image pixel by pixel, line by line'''
        #self.size = (width, totlines)
        i =0
        while i <width:
            self.imagebuffer.append(self.pal[buff[i]])
            i= i+1
                    
        if line == totlines:
            bufferv = self.imagebuffer.tostring()
            try:
                img = Image.frombytes("RGBX", (width, totlines), bufferv) # Pillow
            except:
                img = Image.fromstring("RGBX", (width, totlines), bufferv) # PIL

            imgResize = img.resize((self.size[0], self.size[1]))       
            imgResizeVisual = visual.ImageStim(self.display, image=imgResize)
            
            imgResizeVisual.draw()
            self.draw_cross_hair()    
            self.display.flip()
           
            self.imagebuffer = array.array(self.imgBuffInitType)
            
    def set_image_palette(self, r,g,b):
        '''Given a set of RGB colors, create a list of 24bit numbers representing the pallet.
        I.e., RGB of (1,64,127) would be saved as 82047, or the number 00000001 01000000 011111111'''
        
        self.imagebuffer = array.array(self.imgBuffInitType)
        #self.clear_cal_display()
        sz = len(r)
        i =0
        self.pal = []
        while i < sz:
            rf = int(b[i])
            gf = int(g[i])
            bf = int(r[i])
            self.pal.append((rf<<16) | (gf<<8) | (bf))
            i = i+1



