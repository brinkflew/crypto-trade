import re

from datetime import datetime, timedelta
from itertools import groupby
from sqlalchemy import func
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from trader import Config, Database
from trader.models import Coin, CoinHistory, CoinValue, TradeHistory, ScoutHistory, Pair


app = Flask("trader_api")
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

socketio = SocketIO(app, cors_allowed_origins="*")

config = Config()
database = Database(config)


def filter_period(query, model):
    period = request.args.get("period", "all")  # type: ignore

    if period == "all":
        return query

    num = float(re.search(r"(\d*)[shdwm]", "1d").group(1))  # type: ignore

    if "s" in period:
        return query.filter(model.datetime >= datetime.now() - timedelta(seconds=num))
    if "h" in period:
        return query.filter(model.datetime >= datetime.now() - timedelta(hours=num))
    if "d" in period:
        return query.filter(model.datetime >= datetime.now() - timedelta(days=num))
    if "w" in period:
        return query.filter(model.datetime >= datetime.now() - timedelta(weeks=num))
    if "m" in period:
        return query.filter(model.datetime >= datetime.now() - timedelta(days=28 * num))


@app.route("/api/value_history/<coin>")
@app.route("/api/value_history")
def value_history(coin=None):
    with database.db_session() as session:
        query = session.query(CoinValue).order_by(CoinValue.coin_id.asc(), CoinValue.datetime.asc())  # type: ignore
        query = filter_period(query, CoinValue)
        assert query is not None

        if coin:
            values = query.filter(CoinValue.coin_id == coin).all()
            return jsonify([entry.info() for entry in values])

        coin_values = groupby(query.all(), key=lambda cv: cv.coin)
        return jsonify({coin.symbol: [entry.info() for entry in history] for coin, history in coin_values})


@app.route("/api/total_value_history")
def total_value_history():
    with database.db_session() as session:
        query = session.query(
            CoinValue.datetime,
            func.sum(CoinValue.btc_value),
            func.sum(CoinValue.usd_value),
        ).group_by(CoinValue.datetime)

        query = filter_period(query, CoinValue)
        assert query is not None

        total_values = query.all()
        return jsonify([{"datetime": tv[0], "btc": tv[1], "usd": tv[2]} for tv in total_values])


@app.route("/api/trade_history")
def trade_history():
    with database.db_session() as session:
        query = session.query(TradeHistory).order_by(TradeHistory.datetime.asc())  # type: ignore
        query = filter_period(query, TradeHistory)
        assert query is not None

        trades = query.all()
        return jsonify([trade.info() for trade in trades])


@app.route("/api/scouting_history")
def scouting_history():
    _current_coin = database.get_current_coin()
    coin = _current_coin.symbol if _current_coin is not None else None

    with database.db_session() as session:
        query = (
            session.query(ScoutHistory)
            .join(ScoutHistory.pair)
            .filter(Pair.from_coin_id == coin)
            .order_by(ScoutHistory.datetime.asc())  # type: ignore
        )
        query = filter_period(query, ScoutHistory)
        assert query is not None

        scouts = query.all()
        return jsonify([scout.info() for scout in scouts])


@app.route("/api/current_coin")
def current_coin():
    coin = database.get_current_coin()
    return coin.info() if coin else None


@app.route("/api/current_coin_history")
def current_coin_history():
    with database.db_session() as session:
        query = session.query(CoinHistory)
        query = filter_period(query, CoinHistory)
        assert query is not None

        current_coins = query.all()
        return jsonify([cc.info() for cc in current_coins])


@app.route("/api/coins")
def coins():
    with database.db_session() as session:
        _current_coin = session.merge(database.get_current_coin())
        _coins = session.query(Coin).all()
        return jsonify([{**coin.info(), "is_current": coin == _current_coin} for coin in _coins])


@app.route("/api/pairs")
def pairs():
    with database.db_session() as session:
        all_pairs = session.query(Pair).all()
        return jsonify([pair.info() for pair in all_pairs])


@socketio.on("update", namespace="/backend")
def handle_my_custom_event(json):
    emit("update", json, namespace="/frontend", broadcast=True)


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5123)
