"""
Details the various flask endpoints for processing and retrieving
command details as well as a swagger spec endpoint
"""

from multiprocessing import Process, Queue
import sys,json
from flask import Flask, request, jsonify
from flask_swagger import swagger

from db import session, engine
from base import Base, Command
from command_parser import get_valid_commands, process_command_output, get_valid_commands_using_data
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)


@app.route('/commands', methods=['GET'])
def get_command_output():
    """
    Returns as json the command details that have been processed
    ---
    tags: [commands]
    responses:
      200:
        description: Commands returned OK
      400:
        description: Commands not found
    """

    # TODO: format the query result

    cols = ['id', 'command_string', 'length', 'duration', 'output']

    #query based on the id
    if 'id' in request.args:
        try:
            commands = session.query(Command).get(request.args.get('id'))
            if commands is None:
                resp = jsonify({'No such command id exists': request.args.get('id')})
                resp.status_code = 400
                return resp

            result = {'id':commands.id, 'command_string':commands.command_string, 'length': commands.length, 'duration': commands.duration, 
            'output':commands.output}
            resp =jsonify(result)
            resp.status_code = 200
            return resp

        except IntegrityError as e:
            resp = jsonify({'Integrity Error': str(e)})
            resp.status_code = 400
            return resp

    #query based on the command string
    elif 'command' in request.args:
        try:
            commands=session.query(Command).filter(Command.command_string==request.args.get('command')).one_or_none()
            if commands is None:
                resp = jsonify({'No such command exists': request.args.get('command')})
                resp.status_code = 400
                return resp

            result = {'id':commands.id, 'command_string':commands.command_string, 'length': commands.length, 'duration': commands.duration, 
            'output':commands.output}
            resp =jsonify(result)
            resp.status_code = 200
            return resp

        except IntegrityError as e:
            resp = jsonify({'Integrity Error': str(e)})
            resp.status_code = 400
            return resp

    #fetch all the command list
    else:    
        try:
            commands = session.query(Command)
            result = [{col: getattr(d, col) for col in cols} for d in commands]
            if len(result) == 0:
                resp =jsonify({'Commands not found': None})
                resp.status_code = 400
                return resp
            else:
                resp =jsonify(result=result)
                resp.status_code = 200
                return resp

        except IntegrityError as e:
            resp = jsonify({'Integrity Error': str(e)})
            resp.status_code = 400
            return resp


@app.route('/commands', methods=['POST'])
def process_commands():
    """
    Processes commmands from a command list
    ---
    tags: [commands]
    parameters:
      - name: filename
        in: formData
        description: filename of the commands text file to parse
        required: true
        type: string
    responses:
      200:
        description: Processing OK
    """
    fi = request.args.get('filename')

    queue = Queue()
    # If the argument contains 'file_data' then the commands data is coming from POST body
    if 'file_data' in request.args:
        get_valid_commands_using_data(queue,data=request.get_data(as_text=False))
    # If the 'commands.txt' file is passed then parse the file     
    else:
        get_valid_commands(queue, fi)
    

    processes = [Process(target=process_command_output, args=(queue,))
                 for num in range(2)]

    for process in processes:
        process.start()
    for process in processes:
        process.join()
    return 'Successfully processed commands.'


@app.route('/database', methods=['POST'])
def make_db():
    """
    Creates database schema
    ---
    tags: [db]
    responses:
      200:
        description: DB Creation OK
    """
    Base.metadata.create_all(engine)
    return 'Database creation successful.'


@app.route('/database', methods=['DELETE'])
def drop_db():
    """
    Drops all db tables
    ---
    tags: [db]
    responses:
      200:
        description: DB table drop OK
    """
    Base.metadata.drop_all(engine)
    return 'Database deletion successful.'


if __name__ == '__main__':
    """
    Starts up the flask server
    """
    port = 8080
    use_reloader = True

    # provides some configurable options
    for arg in sys.argv[1:]:
        if '--port' in arg:
            port = int(arg.split('=')[1])
        elif '--use_reloader' in arg:
            use_reloader = arg.split('=')[1] == 'true'

    app.run(port=port, debug=True, use_reloader=use_reloader)


@app.route('/spec')
def swagger_spec():
    """
    Display the swagger formatted JSON API specification.
    ---
    tags: [docs]
    responses:
      200:
        description: OK status
    """
    spec = swagger(app)
    spec['info']['title'] = "Nervana cloud challenge API"
    spec['info']['description'] = ("Nervana's cloud challenge " +
                                   "for interns and full-time hires")
    spec['info']['license'] = {
        "name": "Nervana Proprietary License",
        "url": "http://www.nervanasys.com",
    }
    spec['info']['contact'] = {
        "name": "Nervana Systems",
        "url": "http://www.nervanasys.com",
        "email": "info@nervanasys.com",
    }
    spec['schemes'] = ['http']
    spec['tags'] = [
        {"name": "db", "description": "database actions (create, delete)"},
        {"name": "commands", "description": "process and retrieve commands"}
    ]
    return jsonify(spec)
