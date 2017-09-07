from FlashSession import FlashSession


# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass


sess = FlashSession(subject_initials='SM', index_number=1, scanner='n', tracker_on=False)

sess.run()
