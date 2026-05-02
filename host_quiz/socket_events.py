from flask import session, request
from flask_socketio import join_room, leave_room, send
from extensions import socketio          # ✅ import shared instance
from shared_state import rooms, live_games
from models.questions import Question
from database import db
from models.quiz_sessions import QuizSession
from datetime import datetime
from models.results import Results
from models.quiz_sessions import QuizSession
from models.user import User
from models.multiplayer_answers import MultiplayerAnswer
from datetime import datetime



@socketio.on('connect')
def connect():
    room = session.get('room')
    name = session.get('name')

    if not room or not name:
        return
    if room not in rooms and room not in live_games:
        leave_room(room)
        return

    if room not in rooms:
        rooms[room] = {"members": 0, "messages": [], "name": [], "sids": {}}

    join_room(room)

    if name == "Host" and room in live_games:
        live_games[room]["host_sid"] = request.sid

    # Track by sid so reconnects don't duplicate the name
    sids = rooms[room].setdefault("sids", {})

    if request.sid not in sids:
        # New connection — check if this name is already taken by another sid
        if name not in rooms[room].get('name', []):
            rooms[room].setdefault('name', []).append(name)
            rooms[room]['members'] += 1
        # Map this sid to the name regardless
        sids[request.sid] = name

    send({
        "members": rooms[room]['members'],
        "name": rooms[room]['name']
    },to=room)
    print(rooms)


@socketio.on('disconnect')
def disconnect(reason=None):
    room = session.get('room')
    name = session.get('name')

    if not room:
        return

    if room in rooms:
        sids = rooms[room].get("sids", {})

        # Remove this sid from tracking
        if request.sid in sids:
            del sids[request.sid]

        # Only remove the name if NO other sid for this player remains
        still_connected = any(n == name for n in sids.values())
        if not still_connected:
            if name in rooms[room].get('name', []):
                rooms[room]['name'].remove(name)
                rooms[room]['members'] -= 1

        if rooms[room]['members'] <= 0:
            del rooms[room]
            return

    if room in rooms:
        send({
            "members": rooms[room]['members'],
            "name": rooms[room]['name']
        }, to=room)
    print(rooms)


@socketio.on('start_quiz')
def start_quiz():
    room = session.get('room')
    quiz_id = session.get('quiz_id')
    qs = QuizSession.query.get(session.get('session_id'))
    if qs:
        qs.status = 'started'
        qs.started_at = datetime.utcnow()
        db.session.commit()
    if room:
        # Count only players (exclude host)
        player_names = [n for n in rooms[room].get('name', []) if n != "Host"]
        player_count = len(player_names)

        live_games[room] = {
            "quiz_id": int(quiz_id),
            "question_index": 0,
            "scores": {},
            "answers_received": 0,
            "host_sid": request.sid,
            "player_count": player_count,
            "session_id": session.get('session_id'),
        }
        socketio.emit("redirect_to_live", to=room, skip_sid=request.sid)
        socketio.emit("host_redirect_to_live", to=request.sid)



@socketio.on("next_question")
def next_question():
    room = session.get("room")
    print("ROOM IN NEXT QUESTION:", room)
    print("LIVE GAMES:", live_games)
    if room not in live_games:
        return

    game = live_games[room]
    quiz_id = game["quiz_id"]
    index = game["question_index"]

    question = Question.query.filter_by(quiz_id=quiz_id).offset(index).first()

    if not question:
        session_id = game.get("session_id")
        quiz_id_val = game.get("quiz_id")

    # Mark session as ended
        if session_id:
            qs = QuizSession.query.get(session_id)
            if qs:
                qs.status = 'ended'
                qs.ended_at = datetime.utcnow()
                db.session.commit()

    # Save each player's score
        for player_name, score in game["scores"].items():
            user = User.query.filter_by(name=player_name).first()
            if user:
                result = Results(
                    quiz_id=quiz_id_val,
                    user_id=user.id,
                    session_id=session_id,
                    total_score=score,
                    played_at=datetime.utcnow()
                )
                db.session.add(result)
        db.session.commit()

        socketio.emit("quiz_finished", game["scores"], to=room)
        return

    options = [
        {"id": opt.id, "text": opt.option_text}
        for opt in question.options
    ]

    game["correct_option"] = next(
        (opt.id for opt in question.options if opt.is_correct), None
    )

    # Reset answer tracking for this question
    game["answers_received"] = 0
    game["answered_sids"] = []  # track who already answered to prevent double submit

    # Recount players in case someone joined/left
    player_names = [n for n in rooms.get(room, {}).get('name', []) if n != "Host"]
    player_count = len(player_names)
    game["player_count"] = player_count

    total_questions = Question.query.filter_by(quiz_id=quiz_id).count()

    socketio.emit("show_question", {
        "question": question.question_text,
        "options": options,
        "time_limit": 15,
        "player_count": player_count,
        "total_questions": total_questions,
        "is_bonus": question.is_bonus,
        "points": question.points,
    }, to=room)

    # Store bonus state so submit_answer can score correctly
    game["is_bonus"] = question.is_bonus
    game["question_points"] = question.points
    game["question_index"] += 1


@socketio.on("submit_answer")
def submit_answer(data):
    room = session.get("room")
    name = session.get("name")

    if room not in live_games:
        return

    game = live_games[room]

    # Prevent the same player from submitting twice
    if request.sid in game.get("answered_sids", []):
        return

    game.setdefault("answered_sids", []).append(request.sid)

    selected_id = data.get("option_id")
    is_correct = selected_id == game.get("correct_option")

    if name not in game["scores"]:
        game["scores"][name] = 0

    if is_correct:
        pts = game.get("question_points", 10)
        if game.get("is_bonus", False):
            pts = pts * 2
        game["scores"][name] += pts

    game["answers_received"] += 1
    player_count = game.get("player_count", 1)

    pts_gained = 0
    if is_correct:
        pts_gained = game.get("question_points", 10)
        if game.get("is_bonus", False):
            pts_gained = pts_gained * 2

    # Save answer record to multiplayer_answers table
    try:
        user_obj = User.query.filter_by(name=name).first()
        # current question: index was already incremented, so use index-1
        q_index = game["question_index"] - 1
        question = Question.query.filter_by(quiz_id=game["quiz_id"]).offset(q_index).first()
        if question:
            mp_answer = MultiplayerAnswer(
                session_id=game.get("session_id"),
                user_id=user_obj.id if user_obj else None,
                player_name=name,
                question_id=question.id,
                selected_option_id=selected_id,
                is_correct=is_correct,
                points_earned=pts_gained,
            )
            db.session.add(mp_answer)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"MultiplayerAnswer save error: {e}")

    #1. Send answer result ONLY to the player who just answered
    socketio.emit("answer_result", {
        "is_correct": is_correct,
        "your_score": game["scores"][name],
        "points_gained": pts_gained,
    }, to=request.sid)

    #2. Send live scoreboard update ONLY to the host
    socketio.emit("show_scoreboard", {
        "scores": game["scores"],
        "answered": game["answers_received"],
        "total_players": player_count,
    }, to=game["host_sid"])

    #3. If ALL players answered → broadcast scoreboard to everyone in the room
    if game["answers_received"] >= player_count:
        socketio.emit("show_scoreboard_all", {
            "scores": game["scores"],
        }, to=room)

@socketio.on("time_up")
def time_up():
    room = session.get("room")
    if room not in live_games:
        return
    game = live_games[room]

    # Add 0 score for any player who never answered this question
    player_names = [n for n in rooms.get(room, {}).get('name', []) if n != "Host"]
    for name in player_names:
        if name not in game["scores"]:
            game["scores"][name] = 0

    # Broadcast to everyone (host's timer triggered this)
    socketio.emit("show_scoreboard_all", {
        "scores": game["scores"],
    }, to=room)



