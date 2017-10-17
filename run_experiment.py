from FlashSession import *

# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass

# Kill Finder during execution (this will be fun)
applescript="\'tell application \"Finder\" to quit\'"
shellCmd = 'osascript -e '+ applescript
os.system(shellCmd)

# Set nice to -20: extremely high PID priority
new_nice = -20
sysErr = os.system("sudo renice -n %s %s" % (new_nice, os.getpid()))
if sysErr:
    print('Warning: Failed to renice, probably you arent authorized as superuser')


def main():
    initials = raw_input('Your initials: ')
    pp_nr = int(raw_input('Participant number: '))

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

    language = None
    while language not in ['en', 'nl']:
        language = raw_input('What language do you want to use (en/nl)?: ')
        if language not in ['y', 'n']:
            print('I don''t understand that. Please enter ''en'' or ''nl''. What language do you want to use ('
                  'en/nl)?: ')

    sess = FlashSession(subject_initials=initials, index_number=pp_nr, scanner=scanner, tracker_on=tracker_on,
                        language=language)
    sess.run()


if __name__ == '__main__':
    main()
