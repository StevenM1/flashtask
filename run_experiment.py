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
            print('Number must be between 1 and 100.')

    scanner = ''
    simulate = ''
    while scanner not in ['y', 'n']:
        scanner = raw_input('Are you in the scanner (y/n)?: ')
        if scanner not in ['y', 'n']:
            print('I don''t understand that. Please enter ''y'' or ''n''.')

    if scanner == 'n':
        while simulate not in ['y', 'n']:
            simulate = raw_input('Do you want to simulate scan pulses? This is useful during behavioral pilots '
                                 'with eye-tracking (y/n): ')
            if simulate not in ['y', 'n']:
                print('I don''t understand that. Please enter ''y'' or ''n''.')

    # track_eyes = None
    # while track_eyes not in ['y', 'n']:
    #     track_eyes = raw_input('Are you recording gaze (y/n)?: ')
    #     if track_eyes not in ['y', 'n']:
    #         print('I don''t understand that. Please enter ''y'' or ''n''.')

    track_eyes = 'y'
    tracker_on = track_eyes == 'y'

    language = ''
    while language not in ['en', 'nl']:
        language = raw_input('What language do you want to use (en/nl)?: ')
        if language not in ['en', 'nl']:
            print('I don''t understand that. Please enter ''en'' or ''nl''.')

    mirror = False

    block_n = -1
    while block_n not in [0, 1, 2, 3, 4, 5]:
        block_n = int(raw_input("What block do you want to start? Default is 0, last block is 5. "))
        if block_n not in [0, 1, 2, 3, 4, 5]:
            print('I don''t understand that. Please enter a number between 0 and 5 (incl).')

    if block_n > 1:
        try:
            file_dir = os.path.dirname(os.path.abspath(__file__))

            # Find all files with data of this pp
            fn = glob(os.path.join(file_dir, 'data', initials + '_' + str(pp_nr) +
                                   '*.csv'))

            # Ignore files with practice data, and files with data from a single block
            fn = [x for x in fn if 'PRACTICE' not in x and '_block_' not in x]

            # Select last file
            fn = fn[-1]

            # Get score
            start_score = pd.read_csv(fn).tail(1)['score'].values[0]

            check = ''
            while check not in ['y', 'n']:
                print(fn)
                check = raw_input("In the file printed above, it says that the participant scored %d points "
                                  "previously, is this correct? (y/n): " % start_score)
                if check not in ['y', 'n']:
                    print('Enter y or n.')
            if check == 'n':
                start_score = None
                while not -1 < start_score < 561:
                    start_score = int(raw_input("If the subject performed a limbic block in the previous blocks, "
                                                "how many points did he earn there [0-560]?: "))
                    if not -1 < start_score < 561:
                        print("That is not a number between 0 and 561.")
        except:
            print('Could not automatically find previous score...')

            start_score = None
            while not -1 < start_score < 561:
                start_score = int(raw_input("If the subject performed a limbic block in the previous blocks, "
                                            "how many points did he earn there [0-560]?: "))
                if not -1 < start_score < 561:
                    print("That is not a number between 0 and 561.")

    else:
        start_score = 0

    if simulate == 'y':
        # Run with simulated scanner (useful for behavioral pilots with eye-tracking)
        from psychopy.hardware.emulator import launchScan
        sess = FlashSession(subject_initials=initials, index_number=pp_nr, scanner='y', tracker_on=tracker_on,
                            language=language, mirror=mirror, start_block=block_n, start_score=start_score)
        scanner_emulator = launchScan(win=sess.screen, settings={'TR': TR, 'volumes': 30000, 'sync': 't'}, mode='Test')
    else:
        # Run without simulated scanner (useful for a behavioral session with eye-tracking)
        sess = FlashSession(subject_initials=initials, index_number=pp_nr, scanner=scanner, tracker_on=tracker_on,
                            language=language, mirror=mirror, start_block=block_n, start_score=start_score)
    sess.run()


if __name__ == '__main__':
    main()
