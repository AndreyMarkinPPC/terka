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


# projects
@app.route("/api/v1/projects", methods=["GET"])
def projects():
    return _build_response(views.projects(bus.uow))


@app.route("/api/v1/projects/<project_id>", methods=["GET"])
def project(project_id):
    return _build_response(views.project(bus.uow, project_id))


@app.route("/api/v1/project", methods=["POST"])
def new_project():
    data = request.get_json(force=True)
    cmd = commands.CreateProject.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    cmd = commands.DeleteProject(project_id)
    result = bus.handle(cmd)
    return _build_response(result)


# tasks
@app.route("/api/v1/tasks", methods=["GET"])
def tasks():
    return _build_response(views.tasks(bus.uow))


@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def task(task_id):
    return _build_response(views.task(bus.uow, task_id))


@app.route("/api/v1/tasks/<task_id>/commentaries", methods=["GET"])
def task_commentaries(task_id):
    return _build_response(views.task_commentaries(bus.uow, task_id))


@app.route("/api/v1/task", methods=["POST"])
def new_task():
    data = request.get_json(force=True)
    cmd = commands.CreateTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    cmd = commands.DeleteTask(task_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>/comment", methods=["POST"])
def comment_task(task_id):
    data = request.get_json(force=True)
    data.update({"id": task_id})
    cmd = commands.CommentTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


# workspaces
@app.route("/api/v1/workspaces", methods=["GET"])
def workspaces():
    return _build_response(views.workspaces(bus.uow))


@app.route("/api/v1/workspaces/<workspace_id>", methods=["GET"])
def workspace(workspace_id):
    return _build_response(views.workspace(bus.uow, workspace_id))


@app.route("/api/v1/workspaces/<workspace_id>/projects", methods=["GET"])
def workspace_projects(workspace_id):
    return _build_response(views.workspace_projects(bus.uow, workspace_id))


@app.route("/api/v1/workspace", methods=["POST"])
def new_workspace():
    data = request.get_json(force=True)
    cmd = commands.CreateWorkspace.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/workspaces/<workspace_id>", methods=["DELETE"])
def delete_workspace(workspace_id):
    cmd = commands.DeleteWorkspace(workspace_id)
    result = bus.handle(cmd)
    return _build_response(result)


# epics
@app.route("/api/v1/epics", methods=["GET"])
def epics():
    return _build_response(views.epics(bus.uow))


@app.route("/api/v1/epics/<epic_id>", methods=["GET"])
def epic(epic_id):
    return _build_response(views.epic(bus.uow, epic_id))


@app.route("/api/v1/epics/<epic_id>/tasks", methods=["GET"])
def epic_tasks(epic_id):
    return _build_response(views.epic_tasks(bus.uow, epic_id))


@app.route("/api/v1/epic", methods=["POST"])
def new_epic():
    data = request.get_json(force=True)
    cmd = commands.CreateEpic.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/epics/<epic_id>", methods=["DELETE"])
def delete_epic(epic_id):
    cmd = commands.DeleteEpic(epic_id)
    result = bus.handle(cmd)
    return _build_response(result)


#stories
@app.route("/api/v1/stories", methods=["GET"])
def stories():
    return _build_response(views.stories(bus.uow))


@app.route("/api/v1/stories/<story_id>", methods=["GET"])
def story(story_id):
    return _build_response(views.story(bus.uow, story_id))


@app.route("/api/v1/stories/<story_id>/tasks", methods=["GET"])
def story_tasks(story_id):
    return _build_response(views.story_tasks(bus.uow, story_id))


@app.route("/api/v1/story", methods=["POST"])
def new_story():
    data = request.get_json(force=True)
    cmd = commands.CreateStory.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/stories/<story_id>", methods=["DELETE"])
def delete_story(story_id):
    cmd = commands.DeleteStory(story_id)
    result = bus.handle(cmd)
    return _build_response(result)


# sprints
@app.route("/api/v1/sprints", methods=["GET"])
def sprints():
    return _build_response(views.sprints(bus.uow))


@app.route("/api/v1/sprints/<sprint_id>", methods=["GET"])
def sprint(sprint_id):
    return _build_response(views.sprint(bus.uow, sprint_id))


@app.route("/api/v1/sprints/<sprint_id>/tasks", methods=["GET"])
def sprint_tasks(sprint_id):
    return _build_response(views.sprint_tasks(bus.uow, sprint_id))


@app.route("/api/v1/sprint", methods=["POST"])
def new_sprint():
    data = request.get_json(force=True)
    cmd = commands.CreateSprint.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/sprints/<sprint_id>", methods=["DELETE"])
def delete_sprint(sprint_id):
    cmd = commands.DeleteSprint(sprint_id)
    result = bus.handle(cmd)
    return _build_response(result)


# users
@app.route("/api/v1/users", methods=["GET"])
def users():
    return _build_response(views.users(bus.uow))


@app.route("/api/v1/users/<user_id>", methods=["GET"])
def user(user_id):
    return _build_response(views.user(bus.uow, user_id))


@app.route("/api/v1/user", methods=["POST"])
def new_user():
    data = request.get_json(force=True)
    cmd = commands.CreateUser.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    cmd = commands.DeleteUser(user_id)
    result = bus.handle(cmd)
    return _build_response(result)


def _build_response(msg="", status=200, mimetype="application/json"):
    """Helper method to build the response."""
    msg = json.dumps(msg, indent=4, cls=EntityEncoder)
    response = app.response_class(msg, status=status, mimetype=mimetype)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
