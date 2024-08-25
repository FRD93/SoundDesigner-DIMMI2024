class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def c_print(color, text):
    if color == "green":
        return print(bcolors.OKGREEN + text + bcolors.ENDC)
    if color == "cyan":
        return print(bcolors.OKCYAN + text + bcolors.ENDC)
    if color == "blue":
        return print(bcolors.OKBLUE + text + bcolors.ENDC)
    if color == "yellow":
        return print(bcolors.WARNING + text + bcolors.ENDC)
    if color == "red":
        return print(bcolors.FAIL + text + bcolors.ENDC)
