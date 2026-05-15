"""Git safety tests."""

from reducto.git_safety import GitSafety


def test_checkpoint_and_rollback(temp_git_repo):
    git = GitSafety(str(temp_git_repo))
    main = temp_git_repo / "main.py"
    main.write_text("x = 2\n")
    assert not git.is_clean()
    git.create_checkpoint("checkpoint")
    assert git.is_clean()
    main.write_text("x = 99\n")
    assert not git.is_clean()
    git.rollback()
    assert git.is_clean()
    assert main.read_text() == "x = 1\n"
