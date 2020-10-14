from flask import Flask, render_template, Response, request, session, jsonify
from flask_socketio import SocketIO, send, emit, join_room, leave_room, rooms
import uuid
import datetime


# -------- Custom Library --------------#
from utils.connection_handler.redis_lab import RedisHandler
from utils.log_handler.log_lab import get_logger

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

redis_worker = None
redis_pipe = None
logger_worker = get_logger()


RTMP_URL = "rtmp://18.182.8.76/myapp/{}"
HTTP_VIDEO_URL = "http://18.182.8.76/live?app=myapp&stream={}"

# ---------- API ------------------ #
@app.before_first_request
def before_first_request():
    global redis_worker
    global logger_worker
    global redis_pipe

    if redis_worker is None:
        redis_connection = RedisHandler()
        redis_worker = redis_connection.get_redis_client()
        redis_pipe = redis_worker.pipeline()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/getAdminTicket", methods=["POST"])
def get_uuid():
    ttl = 10 # set token live time DEFAULT: 1hr.
    token = str(uuid.uuid4())

    form = request.form
    username = form.get("username")
    date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    
    logger_worker.info(f"Username : {username} Date Time : {date_time} Token : {token}")

    # Set uuid -> username  auths -> uuid -> username 
    if username and redis_worker.set(f"token:{token}", username, nx=True, ex=ttl) and redis_worker.hset("tokens", token, username):
        return jsonify({"token":str(token)}), 201
    
    return jsonify({"token":None}), 401





# -----------Socket Connect --------------------#
@socketio.on('connect')
def connect_handler():
    if redis_worker is not None:
        token = request.args.get("token")
        username = redis_worker.hget("tokens", token)
        if username:
            sid = request.sid
            _ip = request.remote_addr
            date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

            if redis_worker.hmset(f"{username}:{sid}", 
                                    {"remote_ip": _ip, 
                                    "admin_time": date_time}) and redis_worker.hset("connection", sid, username):

                logger_worker.info(f"Client connected : {sid}\tIP : {_ip}")
            
            else:
                logger_worker.error(f"{username}:{sid} connnect fail.")
                return False
        else:
            return False
    else:
        return False

# -----------Socket Disconnect --------------------#
#FIXME: delete room if not exists.
@socketio.on('disconnect')
def disconnect_handler():
    sid = request.sid
    _ip = request.remote_addr
    username = redis_worker.hget("connection", sid)
    room = redis_worker.hget(f"{username}:{sid}", "room")
    redis_worker.hdel("connection", sid)
    if room:
        redis_pipe.hdel(f"{username}:{sid}", "remote_ip", "admin_time", "room")
        redis_pipe.hdel(room, sid)
        redis_pipe.execute()
    else:
        redis_pipe.hdel(f"{username}:{sid}", "remote_ip", "admin_time")
        redis_pipe.execute()


    logger_worker.info(f"Goodbye {username}")


# -----------Socket Join / Leave room --------------------#
@socketio.on('join_room')
def join_room_event_handler(data):
    device = data.get("device")
    username = data.get("username")
    room = data.get("room")
    sid = request.sid
    logger_worker.debug(f"Device : {device} username : {username} sid : {sid} room : {room}")

    connect_username = redis_worker.hget("connection", sid)
    redis_worker.hincrby("rooms", room, amount=1)

    if connect_username == username:
        if redis_worker.hmset(f"{username}:{sid}", {"room": room}): # Valid if username in db

            if redis_worker.hset(room, sid, username):
                join_room(room)
                return "ack", 201

    else:
        return f"Username {username} not in connection list", 401



@socketio.on('leave_room')
def leave_room_event_handler(data):
    device = data.get("device")
    username = data.get("username")
    room = data.get("room")
    sid = request.sid
    logger_worker.debug(f"Device : {device} username : {username} sid : {sid} room : {room}")

    connect_username = redis_worker.hget("connection", sid)
    connect_room = redis_worker.hget(f"{username}:{sid}", "room")


    if connect_username == username and connect_room == room:
        redis_pipe.hset(f"{username}:{sid}", "room", "")
        redis_pipe.hincrby("rooms", room, amount=-1)
        redis_pipe.hdel(room, sid)
        redis_pipe.execute()
        leave_room(room)
        return "ack", 201

    else:
        logger_worker.error(f"{username!r} or {room!r} not in connection list")
        return f"Username {username!r} or room {room!r} not in connection list", 401




# -----------Socket Request Center -------------------------#
@socketio.on("request_center")
def reqeust_center_handler(data):
    device = data.get("device")
    username = data.get("username")
    isVideo = data.get("isVideo")
    isDetection = data.get("isDetect")
    signal_feq = data.get("signal_feq")
    room = data.get("room")

    sid = request.sid
    uid = str(uuid.uuid4())
    connect_username = redis_worker.hget("connection", sid)

    if connect_username:
        if isVideo is True:
            date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            redis_pipe.set(f"vt:{uid}", f"{connect_username}:{sid}", ex=60)
            redis_pipe.hset(f"{connect_username}:{sid}", "video_token", uid)
            redis_pipe.execute()

            send_to_web_data = {"username":username, "device":device, "room":room, "video_url":HTTP_VIDEO_URL.format(uid)}

            socketio.emit("receive_request", send_to_web_data, broadcast=True)

            return RTMP_URL.format(uid), 201

        
        else:
            send_to_web_data = {"username":username, "device":device, "room":room}
            socketio.emit("receive_request", send_to_web_data, broadcast=True)

            return "ack", 201
    else:
        logger_worker.error(f"{connect_username} not in connection list.")
        return f"Access Error",401




@socketio.on("terminated_center")
def terminated_center_handler(data):
    pass




# -----------Send Data --------------------------------------#
@socketio.on("send_data")
def handler_send_data(data):
    device = data.get('device', "none").lower()
    username = data.get('username', "none").lower()
    room = data.get('room', "none")
    save_send_data(TODAY, username, device, data)




@socketio.on("ping")
def test(data):
    socketio.emit("pong", {"Helloworld":123})













def ack(msg):
    print(f'message was received! : {msg}')






if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=8080)