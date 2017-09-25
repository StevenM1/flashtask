#!/usr/bin/env python
# encoding: utf-8

# Parameters of the flashing circles
parameters = {
    'n_flashers': 2,        # Number of choice options
    'increment_length': 7,  # Duration of a flash + pause ('increment')
    'flasher_size': 1,      # in cm?
    'flash_length': 3,      # Duration of the flash itself in frames on a 60Hz screen
    'prop_correct': 0.7,    # Probability of flashing on every increment for the correct answer
    'prop_incorrect': 0.4,  # Probability of flashing on every increment for the incorrect answers
    'radius': 3             # Radius: distance of flashers from center in cm
}

# Trial phase timing
phase_durations = [0.5,  # fixation cross
                   4.8,  # Cue time
                   5,  # fix cross again 0-500ms jittered
                   1.5,  # stimulus maximum time
                   0.35,  # feedback
                   1]    # ITI

# Information about the screen
background_color = (0.5, 0.5, 0.5)  # -0.75,-0.75,-0.75)
screen_res = (2560, 1440)
monitor_name = 'u2715h'
# screen_res = (1280, 800)
# monitor_name = 'laptop'

# Design path
design_path = '/users/steven/Documents/Syncthing/PhDprojects/subcortex/designs'

# Manipulation type
session_type = 'cognitive'  # one of {'motor', 'limbic', 'cognitive'}
response_type = 'keyboard'  # Response options: 'saccade' or 'keyboard'. Ignored if session_type is 'motor'
response_keys = ['z', 'm']  # Order: left, right. Ignored if response_type = 'saccade'


# Total number of trials
n_trials = 240
