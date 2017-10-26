from FlashSession import *

# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass

try:
    # Kill Finder during execution (this will be fun)
    applescript="\'tell application \"Finder\" to quit\'"
    shellCmd = 'osascript -e '+ applescript
    os.system(shellCmd)
except:
    pass

# Set nice to -20: extremely high PID priority
new_nice = -20
sysErr = os.system("sudo renice -n %s %s" % (new_nice, os.getpid()))
if sysErr:
    print('Warning: Failed to renice, probably you arent authorized as superuser')


def main():
    initials = raw_input('Your initials: ')

    pp_nr = 0
    while not 0 < pp_nr < 101:
        pp_nr = int(raw_input('Participant number: '))
        if not 0 < pp_nr < 101:
            print('Number must be between 1 and 100. What is the participant number?: ')

    scanner = None
    while scanner not in ['y', 'n']:
        scanner = raw_input('Are you in the scanner (y/n)?: ')
        if scanner not in ['y', 'n']:
            print('I don''t understand that. Please enter ''y'' or ''n''. Are you in the scanner?: ')

    track_eyes = None
    while track_eyes not in ['y', 'n']:
        track_eyes = raw_input('Are you recording gaze (y/n)?: ')
        if track_eyes not in ['y', 'n']:
            print('I don''t understand that. Please enter ''y'' or ''n''. Are you recording gaze?: ')

    if track_eyes == 'y':
        tracker_on = True
    elif track_eyes == 'n':
        tracker_on = False

    language = ''
    while language not in ['en', 'nl']:
        language = raw_input('What language do you want to use (en/nl)?: ')
        if language not in ['en', 'nl']:
            print('I don''t understand that. Please enter ''en'' or ''nl''. What language do you want to use ('
                  'en/nl)?: ')

    # mirror = None
    # while mirror not in ['y', 'n']:
    #     mirror = raw_input('Are you in the mock scanner? (y/n)')
    #     if mirror not in ['y', 'n']:
    #         print('I don''t understand that. Please enter ''y'' or ''n''. Are in the mock scanner?: ')
    #
    # if mirror == 'y':
    #     mirror = True
    # elif mirror == 'n':
    mirror = False

    block_n = -1
    while block_n not in [0, 1, 2, 3, 4, 5]:
        block_n = int(raw_input("What block do you want to start? Default is 0, last block is 5. "))
        if block_n not in [0, 1, 2, 3, 4, 5]:
            print('I don''t understand that. Please enter a number between 0 and 5 (incl). What block do you want to '
                  'start?: ')

    if block_n > 1:
        start_score = None
        while not -1 < start_score < 561:
            start_score = int(raw_input("If the subject performed a limbic block in the previous blocks, "
                                        "how many points did he earn there [0-560]?: "))
            if not -1 < start_score < 561:
                int(raw_input("That is not a number between 0 and 561. If the subject performed a limbic block in the "
                              "previous blocks, how many points did s/he earn there [0-560; 0 if no limbic block "
                              "was done]?: "))
    else:
        start_score = 0


    sess = FlashSession(subject_initials=initials, index_number=pp_nr, scanner=scanner, tracker_on=tracker_on,
                        language=language, mirror=mirror, start_block=block_n, start_score=start_score)
    sess.run()


if __name__ == '__main__':
    main()
