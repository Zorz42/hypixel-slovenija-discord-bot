import subprocess
from enum import Enum, auto


class StopAction(Enum):
    NONE = auto()
    SHUTDOWN = auto()
    RESTART = auto()
    UPDATE = auto()


while True:
    print("Starting bot")
    stop_action = StopAction.NONE
    process = subprocess.Popen(['python3', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output_buffer = ""
    for c in iter(lambda: process.stdout.read(1), b''):
        output_char = c.decode("utf-8")
        if output_char == "\n":
            if output_buffer == "Shutdown":
                stop_action = StopAction.SHUTDOWN
            elif output_buffer == "Restart":
                stop_action = StopAction.RESTART
            elif output_buffer == "Update":
                stop_action = StopAction.UPDATE
            print(output_buffer)
            output_buffer = ""
        else:
            output_buffer += output_char
    process.wait()

    if stop_action == StopAction.NONE:
        print("Bot has crashed")
    elif stop_action == StopAction.SHUTDOWN:
        print("Bot has shutdown")
        break
    elif stop_action == StopAction.RESTART:
        print("Bot is restarting")
