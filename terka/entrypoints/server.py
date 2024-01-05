import os
from datetime import datetime, date
from flask import Flask, request, render_template, send_from_directory
import json
from json import JSONEncoder

from terka import bootstrap
from terka.domain import commands
from terka.service_layer import views, unit_of_work
from terka.utils import load_config

app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

HOME_DIR = os.path.expanduser("~")
DB_URL = f"sqlite:////{HOME_DIR}/.terka/tasks.db"
STATIC_DIR = os.getenv("STATIC_DIR") or "static"
config = load_config(HOME_DIR)

bus = bootstrap.bootstrap(start_orm=True,
                          uow=unit_of_work.SqlAlchemyUnitOfWork(DB_URL),
                          config=config)


class EntityEncoder(JSONEncoder):

    def default(self, o):
        if isinstance(o, date):
            return o.strftime("%Y-%m-%d %H:%M:%s")
        else:
            return o.__dict__


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    file_requested = os.path.join(app.root_path, STATIC_DIR, path)
    if not os.path.isfile(file_requested):
        path = "index.html"
    max_age = 0 if path == "index.html" else None
    return send_from_directory(STATIC_DIR, path, max_age=max_age)


@app.route("/api/v1/projects", methods=["GET"])
def projects():
    return _build_response(views.projects(bus.uow))


@app.route("/api/v1/projects/<project_id>", methods=["GET"])
def project(project_id):
    return _build_response(views.project(bus.uow, project_id))


@app.route("/api/v1/tasks", methods=["GET"])
def tasks():
    return _build_response(views.tasks(bus.uow))


@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def task(task_id):
    return _build_response(views.task(bus.uow, task_id))


def _build_response(msg="", status=200, mimetype="application/json"):
    """Helper method to build the response."""
    msg = json.dumps(msg, indent=4, cls=EntityEncoder)
    response = app.response_class(msg, status=status, mimetype=mimetype)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
