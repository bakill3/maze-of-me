import os
import platform

def clear_screen() -> None:
    """
    Clears the terminal screen in a cross-platform way.
    """
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')
