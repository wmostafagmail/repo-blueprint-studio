from backend.app.utils.url_validation import is_safe_github_url

def test_valid_github_urls():
    assert is_safe_github_url("https://github.com/octocat/Spoon-Knife") is True
    assert is_safe_github_url("http://github.com/django/django.git") is True
    assert is_safe_github_url("https://sub.github.com/some/repo") is True

def test_invalid_schemes():
    assert is_safe_github_url("ftp://github.com/octocat/Spoon-Knife") is False
    assert is_safe_github_url("git@github.com:octocat/Spoon-Knife.git") is False # git protocol not allowed via http/https validation
    assert is_safe_github_url("github.com/octocat/Spoon-Knife") is False

def test_unsafe_hostnames():
    assert is_safe_github_url("https://localhost/octocat/Spoon-Knife") is False
    assert is_safe_github_url("https://127.0.0.1/octocat/Spoon-Knife") is False
    assert is_safe_github_url("https://192.168.1.1/octocat/Spoon-Knife") is False
    assert is_safe_github_url("https://google.com/octocat/Spoon-Knife") is False

def test_shell_injection_protection():
    assert is_safe_github_url("https://github.com/octocat/Spoon-Knife;ls") is False
    assert is_safe_github_url("https://github.com/octocat/Spoon-Knife&&rm -rf /") is False
    assert is_safe_github_url("https://github.com/octocat/Spoon-Knife`id` ") is False
    assert is_safe_github_url("https://github.com/octocat/Spoon-Knife$(whoami)") is False
