#!/usr/bin/env python
# encoding: utf-8

# Parameters of the flashing circles
parameters = {
    'n_flashers': 2,        # Number of choice options
    'increment_length': 7,  # Duration of a flash + pause ('increment'), in frames
    'flasher_size': 0.6,      # Size of flashing circles (radius) in degrees
    'flash_length': 3,      # Duration of the flash itself in frames on a 60Hz screen
    'prop_correct': 0.7,    # Probability of flashing on every increment for the correct answer
    'prop_incorrect': 0.4,  # Probability of flashing on every increment for the incorrect answers
    'radius_deg': 1.5,      # Radius: distance of flashers from center in degrees
}

fix_cross_parameters = {
    'outer_radius_degrees': 0.3,
    'inner_radius_degrees': 0.15
}

visual_sizes = {
    'cue_object': 3,
    'fb_text': 1,
    'arrows': .25,
    'crosses': 1,
}


# For screenshots ONLY
fix_cross_parameters = {
    'outer_radius_degrees': 1,
    'inner_radius_degrees': .5
}

visual_sizes = {
    'cue_object': 3,
    'fb_text': 2,
    'arrows': .5,
    'crosses': 3,
}

parameters = {
    'n_flashers': 2,        # Number of choice options
    'increment_length': 7,  # Duration of a flash + pause ('increment'), in frames
    'flasher_size': 2,      # Size of flashing circles (radius) in degrees
    'flash_length': 3,      # Duration of the flash itself in frames on a 60Hz screen
    'prop_correct': 0.7,    # Probability of flashing on every increment for the correct answer
    'prop_incorrect': 0.4,  # Probability of flashing on every increment for the incorrect answers
    'radius_deg': 1.5,      # Radius: distance of flashers from center in degrees
}



# MR parameter
TR = 3

# Information about the screen
background_color = (0.5, 0.5, 0.5)  # -0.75,-0.75,-0.75)
# screen_res = (2560, 1440)
screen_res = (2560, 1440)
monitor_name = 'u2715h'
# screen_res = (1280, 800)
# monitor_name = 'laptop'
# screen_res = (1680, 1050)
# monitor_name = '2208WFP'

# Path to find the designs of all participants
design_path = '/users/steven/Documents/Syncthing/PhDprojects/subcortex/flashtask/designs'

# Keyboard response keys
response_keys = ['z', 'm']  # Order: left, right.


# Do you want to keep track of frame lengths? Recommended
record_intervals = True
