import os, platform
def clear_screen():
    os.system("cls" if platform.system()=="Windows" else "clear")
