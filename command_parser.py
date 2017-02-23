"""
Handles the work of validating and processing command input.
"""
from sets import Set
import os, time, json
from base import Command
import subprocess
from db import session, engine
from threading import Thread, Event

TIMEOUT = 60

def get_valid_commands(queue, fi):
    # TODO: efficiently evaluate commands
    commands_list = list()
    valid_commands = Set([])
    with open(fi,"r") as infile:
        for line in infile:
            if line.strip() == '[COMMAND LIST]' or  line.strip() == '':
                continue
            elif line.strip() == '[VALID COMMANDS]':
                break
            else:
                commands_list.append(line.strip())

        for line in infile:
            valid_commands.add(line.strip())
        
    for command in commands_list:
        if command in valid_commands:
            queue.put(command)
    

def process_command_output(queue):
    # TODO: run the command and put its data in the db
    while not queue.empty():
        command = queue.get()
        output_list = []
        ts = time.time()

        #for line in run_command(command):
        #    output_list.append(line)
        output, err = run_command(command)

        obj = json.dumps({'output':output.strip(),'err':err})
        
        te = time.time()
        elapsed_time = te - ts
        if elapsed_time > 60:
            elapsed_time = 0

        cmd = Command(command,len(command), int(elapsed_time), obj)
        session.add(cmd)
        session.commit()


def run_command(command):
    """Helper function to run the commands"""
    done = Event()
    proc = subprocess.Popen(command,shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)

    watcher = Thread(target=kill_on_timeout, args=(done, 5, proc))
    watcher.daemon = True
    watcher.start()

    data, stderr = proc.communicate()
    done.set()

    return data, stderr

def kill_on_timeout(done, timeout, proc):
    """Helper function to kill the running command
        after the timeout"""
    if not done.wait(timeout):
        proc.kill()
    #return iter(subp.stdout.readline, b'')



