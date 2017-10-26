from FlashSession import *
from psychopy.hardware.emulator import launchScan
from psychopy import core

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

    pp_nr = 0
    while not 0 < pp_nr < 101:
        pp_nr = int(raw_input('Participant number: '))
        if not 0 < pp_nr < 101:
            print('Number must be between 1 and 100. What is the participant number?: ')

    scanner = 'n'
    tracker_on = True

    language = ''
    while language not in ['en', 'nl']:
        language = raw_input('What language do you want to use (en/nl)?: ')
        if language not in ['en', 'nl']:
            print('I don''t understand that. Please enter ''en'' or ''nl''. What language do you want to use ('
                  'en/nl)?: ')

    sess = FlashPracticeSession(subject_initials=initials, index_number=pp_nr, scanner=scanner, tracker_on=tracker_on,
                                language=language)
    # Launch dummy scanner
    sess.scanner = launchScan(win=sess.screen, settings={'TR': TR, 'volumes': 10000, 'sync': 't'}, mode='Test')

    sess.run()


if __name__ == '__main__':
    main()

    # Force python to quit (so scanner is also stopped)
    core.quit()