# Module that clears the screen and prints the USBCreate Logo
api = 2.1
from subprocess import call
def module(task_id):
    if task_id != 98:
        call(['clear'])
        print('################################# USBCreate ###################################\n')
    return['-3', '-3', '-3', '-3', '-3', []]
