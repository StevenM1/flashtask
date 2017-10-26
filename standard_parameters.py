#!/usr/bin/env python
# encoding: utf-8

# Parameters of the flashing circles
parameters = {
    'n_flashers': 2,        # Number of choice options
    'increment_length': 7,  # Duration of a flash + pause ('increment'), in frames. 7 is default on 60Hz
    'flasher_size': 0.6,    # Size of flashing circles (radius) in degrees
    'flash_length': 3,      # Duration of the flash itself in frames. 3 is default on 60Hz.
    'prop_correct': 0.7,    # Probability of flashing on every increment for the correct answer
    'prop_incorrect': 0.4,  # Probability of flashing on every increment for the incorrect answers
    'radius_deg': 1.5,      # Radius: distance of flashers from center in degrees
}

fix_cross_parameters = {
    'outer_radius_degrees': 0.3,
    'inner_radius_degrees': 0.15
}

visual_sizes = {
    'cue_object': 1,
    'fb_text': 1,
    'arrows': .25,
    'crosses': 1,
}

# in the SAT condition, "too slow" is probabilistically given as feedback whenever participants are slower than x
# seconds on a speed-trial. Currently, x is set to 1.0 seconds, with the probability of "too slow"-feedback for
# slower responses to 0.6.
sat = {
    'speed_max_time': 1.0,
    'acc_max_time': 1.5,
    'prob_too_slow_fb': .6
}

# MR parameter
TR = 3

# Information about the screen
background_color = (0.5, 0.5, 0.5)  # -0.75,-0.75,-0.75)
screen_res = (2560, 1440)
monitor_name = 'u2715h'

# monitor_name = 'boldscreen'
# screen_res = (1920, 1080)

# monitor_name = 'laptop'
# screen_res = (1280, 800)

# monitor_name = '2208WFP'
# screen_res = (1680, 1050)

from psychopy.monitors import Monitor
cur_mon = Monitor(name='this_monitor', width=57.2, distance=60)
cur_mon.setSizePix(screen_res)
cur_mon.saveMon()
monitor_name='this_monitor'

# Path to find the designs of all participants
design_path = '/users/steven/Documents/Syncthing/PhDprojects/subcortex/flashtask/designs'

# Keyboard response keys
response_keys = ['z', 'm']  # Order: left, right.

# Do you want to keep track of frame lengths? Recommended
record_intervals = True

# adjustments for in MRI scanner
if monitor_name == 'boldscreen':
    # Adjust for 120Hz
    parameters['increment_length'] = parameters['increment_length'] * 2
    parameters['flash_length'] = parameters['flash_length'] * 2
    response_keys = ['e', 'b']




    ## For screenshots ONLY
# fix_cross_parameters = {
#     'outer_radius_degrees': 1,
#     'inner_radius_degrees': .5
# }
#
# visual_sizes = {
#     'cue_object': 3,
#     'fb_text': 2,
#     'arrows': .5,
#     'crosses': 3,
# }
#
# parameters = {
#     'n_flashers': 2,        # Number of choice options
#     'increment_length': 7,  # Duration of a flash + pause ('increment'), in frames
#     'flasher_size': 2,      # Size of flashing circles (radius) in degrees
#     'flash_length': 3,      # Duration of the flash itself in frames on a 60Hz screen
#     'prop_correct': 0.7,    # Probability of flashing on every increment for the correct answer
#     'prop_incorrect': 0.4,  # Probability of flashing on every increment for the incorrect answers
#     'radius_deg': 1.5,      # Radius: distance of flashers from center in degrees
# }