import tracker

if __name__ == "__main__":
    try:
        tracker.run()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg

            print_error_msg(e)
        except ImportError:
            print(e)
