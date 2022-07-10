from flask import jsonify


class LogicAbort:
    @staticmethod
    def abort(base, code):
        base["errorCode"] = code
        return jsonify(base)
