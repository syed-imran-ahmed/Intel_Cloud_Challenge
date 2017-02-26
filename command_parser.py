"""
Handles the work of validating and processing command input.
"""
from sets import Set
import os, time, json, math
from base import Command
import subprocess
from db import session, engine
from sqlalchemy import exists
from threading import Thread, Event
from sqlalchemy.exc import IntegrityError,SQLAlchemyError

TIMEOUT = 60

def get_valid_commands(queue, fi):
    # TODO: efficiently evaluate commands
    """parsing the commands.txt file to make a list of commands
    and make a set for valid commands to put it into the queue"""
    commands_list = list()
    valid_commands = Set([])
    with open(fi,"r") as infile:
        for line in infile:
            print line
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
    

def get_valid_commands_using_data(queue, data):
    """Parse the POST raw data and add it to the queue"""
    commands_list = list()
    valid_commands = Set([])
    lines = data.split('\n')
    count=0
    for line in lines:
            print line
            if line.strip() == '[COMMAND LIST]' or  line.strip() == '':
                count+=1
                continue
            elif line.strip() == '[VALID COMMANDS]':
                count+=1
                break
            else:
                commands_list.append(line.strip())
                count+=1

    for line in lines[count:]:
        valid_commands.add(line.strip())
            
    for command in commands_list:
        if command in valid_commands:
            queue.put(command)


def process_command_output(queue):
    # TODO: run the command and put its data in the db
    """1.Get each command from the queue and run it in its own shell
       2.Clock the runtine of each command and convert it to nearest second
       3.Check if the command is already there in the db, if not then add it
       to the database."""

    while not queue.empty():
        command = queue.get()
        output_list = []

        ts = time.time()
        output, err = run_command(command)
        obj = json.dumps({'output':output.strip(),'error':err})
        te = time.time()

        elapsed_time = te - ts
        if elapsed_time > 60:
            elapsed_time = 0
        else:
            elapsed_time = math.ceil(elapsed_time)
        
        #Checking for duplicate commands in db
        try:
            cmd_db = session.query(exists().where(Command.command_string==command)).scalar()

        except IntegrityError as e:
            cmd_db = False

        
        #Add it to db if command not present in db
        if not cmd_db:
            try:
                cmd = Command(command,len(command), elapsed_time, obj)
                session.add(cmd)
                session.commit()

            except IntegrityError as e:
                session.rollback()
                print "Integrity Error:" + str(e)

            except SQLalchemyError as e:
                session.rollback()
                print "Could Not insert the data" + str(e) 

        
def run_command(command):
    """Helper function to run the commands"""
    done = Event()
    proc = subprocess.Popen(command,shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)

    watcher = Thread(target=kill_on_timeout, args=(done, TIMEOUT, proc))
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
    



