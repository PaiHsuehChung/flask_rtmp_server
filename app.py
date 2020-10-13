from flask import Flask, render_template, Response, request, session, jsonify
from flask_socketio import SocketIO, send, emit, join_room, leave_room
import uuid


# -------- Custom Library --------------#
from utils.connection_handler.redis_lab import RedisHandler
from utils.log_handler.log_lab import get_logger

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

redis_worker = None
logger_worker = get_logger()

# ---------- API ------------------ #
@app.before_first_request
def before_first_request():
    global redis_worker
    global logger_worker

    redis_connection = RedisHandler()
    redis_worker = redis_connection.get_redis_client()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/getLiveTicket", methods=["POST"])
def get_uuid():
    ttl = 100 # set token live time DEFAULT: 1hr.
    uid = str(uuid.uuid4())

    form = request.form
    username = form.get("username")
    
    logger_worker.info(f"Username : {username}")
    
    if username and redis_worker.set(uid, username, nx=True, ex=ttl):
        return jsonify({"uuid":str(uid)}), 201
    
    return jsonify({"uuid":None}), 401





# -----------Socket --------------------#
@socketio.on('connect')
def test_connect():
    print('Client connected : {}\tIP : {}'.format(
        request.sid, request.remote_addr))

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected : {}\tIP : {}'.format(request.sid,
                                                               request.remote_addr))



@socketio.on("receive")
def test_receive_data(data):
    print(data)
    return "hey", 20
    #emit('response', data, callback=ack)


@socketio.on("response")
def test_response_data(data):
    print(data)


def ack(msg):
    print(f'message was received! : {msg}')






if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=8080)