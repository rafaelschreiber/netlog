import os
from time import localtime, strftime

sessiontimecode = strftime("%Y-%m-%d_%H-%M-%S", localtime())

def Log(content, severity=0):
    global sessiontimecode

    current_time = "[" + strftime("%Y-%m-%d %H:%M:%S", localtime()) + "]"

    if severity == 0 or severity == "info":
        log = current_time + " !️  " + str(content)
    elif severity == 1 or severity == "error":
        log = current_time + " ✘  " + str(content)
    elif severity == 2 or severity == "ok":
        log = current_time + " ✔  " + str(content)
    elif severity == -1 or severity == "debug":
        log = current_time + " !! " + str(content)
    else:
        return


    if not os.path.exists("logs"):
        os.makedirs("logs/")
    with open("logs/log_" + sessiontimecode + ".txt", "a+") as file:
        file.write(log + '\n')
        print(log)
        file.close()
        os.system("ln -sf log_"  + sessiontimecode + ".txt logs/latest")