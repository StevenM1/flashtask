parameters = {
    'n_flashers': 2,  # Number of choice options
    'increment_length': 7,  # Duration of a flash + pause ('increment')
    'flasher_size': 1,  # in cm?
    'flash_length': 3,  # Duration of the flash itself
    'prop_correct': 0.7,  # Probability of flashing on every increment for the correct answer
    'prop_incorrect': 0.4,  # Probability of flashing on every increment for the incorrect answers
    'radius': 3,  # Radius: distance of flashers from center in cm
}

response_keys = ['z', 'm']  # Order: left, right

n_trials = 5

phase_durations = [-.0001,  # instruction time
                   0.5,  # fixation cross
                   1.5,  # stimulus maximum time
                   0.5,  # feedback
                   1]  # ITI
background_color = (0.5, 0.5, 0.5)  # -0.75,-0.75,-0.75)

screen_res = (1680, 1050)
monitor_name = '2208WFP'
