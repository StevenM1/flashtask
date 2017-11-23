#!/usr/bin/env python
# encoding: utf-8
import os

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

# Parameters of the fixation cross. See
fix_cross_parameters = {
    'outer_radius_degrees': 0.3,
    'inner_radius_degrees': 0.1
}

visual_sizes = {
    'cue_object': 1,
    'fb_text': 1,
    'arrows': 5,  # If arrows = 5, draws arrows of size (2, 1) in degrees (2 horizontal degrees, 1 vertical degree)
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

# Information about the screen & display
background_color = (0.5, 0.5, 0.5)

# Path to find the designs of all participants
design_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'designs')

# Do you want to keep track of frame lengths? Recommended
record_intervals = True

# Check the following: if the current user is ME, we assume that we're running on my laptop for programming
if 'USER' in os.environ and os.environ['USER'] == 'steven':
    monitor_name = 'u2715h'
    screen_res = (2560, 1440)

    # monitor_name = 'boldscreen'
    # screen_res = (1920, 1080)

    # monitor_name = 'laptop'
    # screen_res = (1280, 800)

    # monitor_name = '2208WFP'
    # screen_res = (1680, 1050)

    # Keyboard response keys
    response_keys = ['z', 'slash']  # Order: left, right.

# Settings for Roeterseiland computers
elif 'HOMEPATH' in os.environ and os.environ['HOMEPATH'] == '\\Users\\User':
    from psychopy.monitors import Monitor
    screen_res = (1920, 1080)
    distance = 55

    # Create Monitor
    cur_mon = Monitor(name='benq', width=53.1, distance=distance, notes='Dynamically created in standard_parameters. '
                                                                          'You might read a warning if the monitor '
                                                                          'specification does not already exist.')
    cur_mon.setSizePix(screen_res)
    cur_mon.saveMon()
    monitor_name = 'benq'
    response_keys = ['z', 'slash']

elif 'HOMEPATH' in os.environ and os.environ['USERNAME'] == 'psyuser':
    from psychopy.monitors import Monitor
    screen_res = (1920, 1080)
    distance = 55

    # Create Monitor
    cur_mon = Monitor(name='asus', width=55, distance=distance, notes='Dynamically created in standard_parameters. '
                                                                          'You might read a warning if the monitor '
                                                                          'specification does not already exist.')
    cur_mon.setSizePix(screen_res)
    cur_mon.saveMon()
    monitor_name = 'asus'
    response_keys = ['z', 'slash']

else:
    # Assumes we are running on the actual, experimental set-up (i.e. 7T-MRI scanner)
    from psychopy.monitors import Monitor
    screen_res = (1920, 1080)
    distance = 225  # 225cm from eyes in bore to screen

    # Create Monitor
    cur_mon = Monitor(name='boldscreen', width=57.2, distance=distance, notes='Dynamically created in standard_parameters. '
                                                                          'You might read a warning if the monitor '
                                                                          'specification does not already exist.')
    cur_mon.setSizePix(screen_res)
    cur_mon.saveMon()
    monitor_name = 'boldscreen'
    response_keys = ['e', 'b']  # Button box keys

    # Adjust for 120Hz
    parameters['increment_length'] = parameters['increment_length'] * 2
    parameters['flash_length'] = parameters['flash_length'] * 2


# # The following settings are used for screenshots ONLY (they increase all sizes).
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
