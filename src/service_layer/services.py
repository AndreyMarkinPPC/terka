from src.adapters.repository import AbsRepository
from src.domain.project import Project
from src.domain.user import User


def lookup_project_id(project_name: str, repo: AbsRepository) -> int:
    projects = project_name.split(",")
    if project_name.startswith("NOT"):
        projects = [
            f"NOT:{project}"
            for project in project_name.replace("NOT:", "").split(",")
        ]
        negate = True
    else:
        projects = project_name.split(",")
        negate = False
    returned_projects = []
    returned_projects_set = set()
    for project_name in projects:
        if not (project := repo.list(Project, project_name)):
            print(
                f"Creating new project: {project_name}. Do you want to continue (Y/n)?"
            )
            answer = input()
            while answer.lower() != "y":
                print("Provide a project name: ")
                project_name = input()
                print(
                    f"Creating new project: {project_name}. Do you want to continue (Y/n)?"
                )
                answer = input()
            project = Project(project_name)
            repo.add(project)
            repo.session.commit()
        if isinstance(project, list):
            project_ids = [project.id for project in project]
            if negate:
                if returned_projects_set:
                    returned_projects_set =returned_projects_set.intersection(set(project_ids))
                else:
                     returned_projects_set = returned_projects_set.union(set(project_ids))

            else:
                returned_projects.extend(project_ids)
        else:
            returned_projects.append(project.id)
    if returned_projects_set:
        return list(returned_projects_set)
    if len(returned_projects) == 1:
        return returned_projects[0]
    return returned_projects


def lookup_user_id(user_name: str, repo: AbsRepository) -> int:
    if not (user := repo.list(User, user_name)):
        user = User(user_name)
        repo.add(user)
    repo.session.commit()
    return user.id


def lookup_project_name(project_id: int, repo: AbsRepository) -> str:
    project = repo.list(Project, {"id": project_id})
    repo.session.commit()
    return project[0]
