from backend.app.utils.repo_name import repo_name_from_url, sanitize_repo_name

def test_repo_name_extraction():
    assert repo_name_from_url("https://github.com/octocat/Spoon-Knife") == "Spoon-Knife"
    assert repo_name_from_url("https://github.com/django/django.git") == "django"
    assert repo_name_from_url("git@github.com:org/some-project.git") == "some-project"

def test_sanitization():
    assert sanitize_repo_name("my_awesome_project.git") == "my_awesome_project"
    assert sanitize_repo_name("project#unsafe$chars") == "project-unsafe-chars"
    assert sanitize_repo_name("   /trail/lead/slash/   ") == "slash"
