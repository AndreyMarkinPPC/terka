import os
from datetime import datetime, date
from flask import Flask, request, render_template, send_from_directory
import json
from json import JSONEncoder

from terka import bootstrap, views
from terka.domain import commands
from terka.service_layer import unit_of_work
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
def list_projects():
    return _build_response(views.projects(bus.uow))


@app.route("/api/v1/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    return _build_response(views.project(bus.uow, project_id))


@app.route("/api/v1/projects/<project_id>", methods=["PATCH"])
def update_project(project_id):
    data = dict(request.values.items())
    data.update({"id": project_id})
    cmd = commands.UpdateProject.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/projects/<project_id>:complete", methods=["POST"])
def complete_project(project_id):
    cmd = commands.CompleteProject(project_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/projects/<project_id>/tasks", methods=["GET"])
def list_project_tasks(project_id):
    return _build_response(views.project_tasks(bus.uow, project_id))


@app.route("/api/v1/projects", methods=["POST"])
def create_project():
    data = request.get_json(force=True)
    cmd = commands.CreateProject.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    cmd = commands.DeleteProject(project_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/projects/<project_id>:tag", methods=["POST"])
def tag_project(project_id):
    data = request.get_json(force=True)
    data.update({"id": project_id})
    cmd = commands.TagProject.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/projects/<project_id>:sync", methods=["POST"])
def sync_project(project_id):
    cmd = commands.SyncProject(project_id)
    result = bus.handle(cmd)
    return _build_response(result)


# tasks
@app.route("/api/v1/tasks", methods=["GET"])
def list_tasks():
    return _build_response(views.tasks(bus.uow))


@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    return _build_response(views.task(bus.uow, task_id))


@app.route("/api/v1/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id):
    data = dict(request.values.items())
    data.update({"id": task_id})
    cmd = commands.UpdateTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>:complete", methods=["POST"])
def complete_task(task_id):
    cmd = commands.CompleteTask(task_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>/commentaries", methods=["GET"])
def list_task_commentaries(task_id):
    return _build_response(views.task_commentaries(bus.uow, task_id))


@app.route("/api/v1/tasks", methods=["POST"])
def create_task():
    data = request.get_json(force=True)
    cmd = commands.CreateTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    cmd = commands.DeleteTask(task_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>:comment", methods=["POST"])
def comment_task(task_id):
    data = request.get_json(force=True)
    data.update({"id": task_id})
    cmd = commands.CommentTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>:tag", methods=["POST"])
def tag_task(task_id):
    data = request.get_json(force=True)
    data.update({"id": task_id})
    cmd = commands.TagTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>:collaborate", methods=["POST"])
def collaborate_task(task_id):
    data = request.get_json(force=True)
    data.update({"id": task_id})
    cmd = commands.CollaborateTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>:track", methods=["POST"])
def track_task(task_id):
    data = request.get_json(force=True)
    data.update({"id": task_id})
    cmd = commands.TrackTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>:add", methods=["POST"])
def add_task(task_id):
    data = request.get_json(force=True)
    data.update({"id": task_id})
    cmd = commands.AddTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tasks/<task_id>:remove", methods=["POST"])
def remove_task(task_id):
    data = request.get_json(force=True)
    data.update({"id": task_id})
    cmd = commands.DeleteTask.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


# workspaces
@app.route("/api/v1/workspaces", methods=["GET"])
def list_workspaces():
    return _build_response(views.workspaces(bus.uow))


@app.route("/api/v1/workspaces/<workspace_id>", methods=["GET"])
def get_workspace(workspace_id):
    return _build_response(views.workspace(bus.uow, workspace_id))


@app.route("/api/v1/workspaces/<workspace_id>/projects", methods=["GET"])
def list_workspace_projects(workspace_id):
    return _build_response(views.workspace_projects(bus.uow, workspace_id))


@app.route("/api/v1/workspaces", methods=["POST"])
def create_workspace():
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
def list_epics():
    return _build_response(views.epics(bus.uow))


@app.route("/api/v1/epics/<epic_id>", methods=["GET"])
def get_epic(epic_id):
    return _build_response(views.epic(bus.uow, epic_id))


@app.route("/api/v1/epics/<epic_id>", methods=["PATCH"])
def update_epic(epic_id):
    data = dict(request.values.items())
    data.update({"id": epic_id})
    cmd = commands.UpdateEpic.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/epics/<epic_id>:complete", methods=["POST"])
def complete_epic(epic_id):
    cmd = commands.CompleteEpic(epic_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/epics/<epic_id>/tasks", methods=["GET"])
def list_epic_tasks(epic_id):
    return _build_response(views.epic_tasks(bus.uow, epic_id))


@app.route("/api/v1/epics", methods=["POST"])
def create_epic():
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
def list_stories():
    return _build_response(views.stories(bus.uow))


@app.route("/api/v1/stories/<story_id>", methods=["GET"])
def get_story(story_id):
    return _build_response(views.story(bus.uow, story_id))


@app.route("/api/v1/stories/<story_id>", methods=["PATCH"])
def update_story(story_id):
    data = dict(request.values.items())
    data.update({"id": story_id})
    cmd = commands.UpdateStory.from_kwargs(**data)


@app.route("/api/v1/stories/<story_id>:complete", methods=["POST"])
def complete_story(story_id):
    cmd = commands.CompleteStory(story_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/stories/<story_id>/tasks", methods=["GET"])
def list_story_tasks(story_id):
    return _build_response(views.story_tasks(bus.uow, story_id))


@app.route("/api/v1/stories", methods=["POST"])
def create_story():
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
def list_sprints():
    return _build_response(views.sprints(bus.uow))


@app.route("/api/v1/sprints/<sprint_id>", methods=["GET"])
def get_sprint(sprint_id):
    return _build_response(views.sprint(bus.uow, sprint_id))


@app.route("/api/v1/sprints/<sprint_id>", methods=["PATCH"])
def update_sprint(sprint_id):
    data = dict(request.values.items())
    data.update({"id": sprint_id})
    cmd = commands.UpdateSprint.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/sprints/<sprint_id>:start", methods=["POST"])
def start_sprint(sprint_id):
    cmd = commands.StartSprint(sprint_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/sprints/<sprint_id>:complete", methods=["POST"])
def complete_sprint(sprint_id):
    cmd = commands.CompleteSprint(sprint_id)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/sprints/<sprint_id>/tasks", methods=["GET"])
def list_sprint_tasks(sprint_id):
    return _build_response(views.sprint_tasks(bus.uow, sprint_id))


@app.route("/api/v1/sprints", methods=["POST"])
def create_sprint():
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
def list_users():
    return _build_response(views.users(bus.uow))


@app.route("/api/v1/users/<user_id>", methods=["GET"])
def get_user(user_id):
    return _build_response(views.user(bus.uow, user_id))


@app.route("/api/v1/users", methods=["POST"])
def create_user():
    data = request.get_json(force=True)
    cmd = commands.CreateUser.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    cmd = commands.DeleteUser(user_id)
    result = bus.handle(cmd)
    return _build_response(result)


# tags
@app.route("/api/v1/tags", methods=["GET"])
def list_tags():
    return _build_response(views.tags(bus.uow))


@app.route("/api/v1/tags/<tag_id>", methods=["GET"])
def get_tag(tag_id):
    return _build_response(views.tag(bus.uow, tag_id))


@app.route("/api/v1/tags", methods=["POST"])
def create_tag():
    data = request.get_json(force=True)
    cmd = commands.CreateTag.from_kwargs(**data)
    result = bus.handle(cmd)
    return _build_response(result)


@app.route("/api/v1/tags", methods=["DELETE"])
def delete_tag():
    data = request.get_json(force=True)
    cmd = commands.DeleteTag.from_kwargs(**data)
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
