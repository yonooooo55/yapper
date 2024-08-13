from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import random
from string import ascii_uppercase


app = Flask(__name__)
app.config['SECRET_KEY'] = "123"
socketio = SocketIO(app)

ROOMS = {}
PUBLIC_ROOMS = {
                    "PB1": {"members": 0, "messages": []},
                    "PB2": {"members": 0, "messages": []},
                    "PB3" :{"members": 0, "messages": []}
                }

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in ROOMS:
            break
    return code


@app.route("/", methods=["GET", "POST"])
def index():
    
    return render_template("index.html")


@app.route("/home", methods=["GET", "POST"])
def home():

    session.clear()

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        
        if not name:
            return render_template("home.html", error="Please enter a username", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code",code=code, name=name)
        
        # Get the room and create one if not existent
        room = code
        if create != False:
            room = generate_unique_code(4)
            ROOMS[room] = {"members": 0, "messages": []}

        elif code not in ROOMS: 
            return render_template("home.html", error="Room does not exist", code=code, name=name)
        

        #SESSION VARIABLES
        session["room"] = room
        session["name"] = name
        
        return redirect(url_for("room"))
        
    return render_template("home.html") 


@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in ROOMS:
        return redirect(url_for("index"))
    
    messages = ROOMS[room]["messages"]
    return render_template("room.html", code=room, messages=messages)

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    isPublicRoom = session.get("isPublicRoom")

    if not room or not name:
        return
    
    #Check if room is public or private
    if isPublicRoom:                        
        if room not in PUBLIC_ROOMS:        # If public room dont exists, leave the room
            leave_room(room)
            return
        else:                               # If the room is a public room, join it
            join_room(room)
            emit("grpm", {"name": name, "message": name + " has joined the room"})
            PUBLIC_ROOMS[room]["members"] += 1
            print(f"{name} has joined {room}")
    else:
        if room not in ROOMS:
            leave_room(room)
            return
        else:
            join_room(room)
            send({"name": name, "message": name + " has joined the room"}, to = room)
            ROOMS[room]["members"] += 1
            print(f"{name} has joined {room}")
    


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    

    #If the room exists, remove the user from the room
    if room in ROOMS:
        ROOMS[room]["members"] -= 1         #Update the count
        if ROOMS[room]["members"] <= 0:     #If no one is in the room, delete it
            del ROOMS[room]
    
    send({"name": name, "message": name + " has left the room"}, to = room)
    emit("disconnected", {"name": name, "message": name + " has left the room"}, to = room)
    leave_room(room)
    print(f"{name} has left {room}")
    
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in ROOMS:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to = room)
    ROOMS[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")



@app.route("/join_public_room", methods=["POST"])
def join_public_room():
    if request.method == "POST":
        anon_username = request.form.get("anon_username")
        pb_room = request.form.get("pb_room_id")
        
    #SESSION VARIABLES
    session["room"] = pb_room
    session["name"] = anon_username
    session["isPublicRoom"] = True

    return redirect(url_for("public_room"))


@app.route("/public_room")
def public_room():
    room = session.get("room")

    if room is None or session.get("name") is None or room not in PUBLIC_ROOMS:
        return redirect(url_for("index"))
    
    messages = PUBLIC_ROOMS[room]["messages"]
    return render_template("public_room.html", code=room, messages=messages)
        

@socketio.on('public_message')
def handle_public_message(data):
    room = session.get('room')

    if room not in PUBLIC_ROOMS:
        return

    content = {
        "name": session.get('name'),
        "message": data["data"]
    }

    # Broadcast message to all clients in the room
    socketio.emit("grpm", content)
    PUBLIC_ROOMS[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")






        
if __name__ == "__main__":
    socketio.run(app, debug=True)
    


