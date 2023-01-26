from src import utils

def test_create_task_dict():
    kwargs = ['-n', 'task_name', '-p', 'project_name', '-a', 'am']
    expected = {'n': 'task_name', 'p': 'project_name', 'a': 'am'}
    task_dict = utils.create_task_dict(kwargs)
    assert task_dict == expected
