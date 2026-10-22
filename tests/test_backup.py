from datetime import datetime

import pytest

from termforge.backup import (
    BackupError,
    create_backup,
    get_backup,
    list_backups,
    restore_backup,
)

T0 = datetime(2026, 10, 21, 20, 0, 0)
T1 = datetime(2026, 10, 21, 20, 5, 0)


@pytest.fixture
def files(tmp_path):
    settings = tmp_path / "wt" / "settings.json"
    profile = tmp_path / "ps" / "profile.ps1"
    settings.parent.mkdir()
    profile.parent.mkdir()
    settings.write_text("settings v1", encoding="utf-8")
    profile.write_text("profile v1", encoding="utf-8")
    return {"windows-terminal": settings, "powershell-profile": profile}


@pytest.fixture
def root(tmp_path):
    return tmp_path / "backups"


def test_create_and_list(files, root):
    info = create_backup(files, root, label="Antes de probar tema!", now=T0)

    assert info.id == "20261021-200000-antes-de-probar-tema"
    assert {e.name for e in info.entries} == set(files)
    assert [b.id for b in list_backups(root)] == [info.id]


def test_only_existing_files_are_backed_up(files, root):
    files["powershell-profile"].unlink()
    info = create_backup(files, root, now=T0)
    assert [e.name for e in info.entries] == ["windows-terminal"]


def test_nothing_to_backup_raises(tmp_path, root):
    with pytest.raises(BackupError):
        create_backup({"x": tmp_path / "no-existe.json"}, root, now=T0)


def test_same_second_does_not_overwrite(files, root):
    a = create_backup(files, root, now=T0)
    b = create_backup(files, root, now=T0)
    assert a.id != b.id
    assert len(list_backups(root)) == 2


def test_list_is_newest_first(files, root):
    old = create_backup(files, root, now=T0)
    new = create_backup(files, root, now=T1)
    assert [b.id for b in list_backups(root)] == [new.id, old.id]
    assert get_backup(root).id == new.id


def test_restore_overwrites_and_keeps_safety_backup(files, root):
    create_backup(files, root, now=T0)
    files["windows-terminal"].write_text("settings v2 (roto)", encoding="utf-8")

    report = restore_backup(root, files, now=T1)

    assert files["windows-terminal"].read_text(encoding="utf-8") == "settings v1"
    assert report.safety_backup is not None
    assert report.safety_backup.label == "pre-restore"
    stored = report.safety_backup.path / "windows-terminal.json"
    assert stored.read_text(encoding="utf-8") == "settings v2 (roto)"


def test_restore_dry_run_changes_nothing(files, root):
    create_backup(files, root, now=T0)
    files["windows-terminal"].write_text("settings v2", encoding="utf-8")

    report = restore_backup(root, files, dry_run=True)

    assert report.dry_run and report.safety_backup is None
    assert files["windows-terminal"].read_text(encoding="utf-8") == "settings v2"
    assert len(list_backups(root)) == 1


def test_restore_recreates_missing_file(files, root):
    create_backup(files, root, now=T0)
    files["powershell-profile"].unlink()

    restore_backup(root, files, now=T1)

    assert files["powershell-profile"].read_text(encoding="utf-8") == "profile v1"


def test_restore_ignores_unknown_targets(files, root):
    create_backup(files, root, now=T0)
    only_one = {"windows-terminal": files["windows-terminal"]}

    report = restore_backup(root, only_one, dry_run=True)

    assert report.skipped == ["powershell-profile"]
    assert [a.name for a in report.actions] == ["windows-terminal"]


@pytest.mark.parametrize("bad_id", ["../fuera", "a/b", "..", "."])
def test_path_traversal_ids_are_rejected(root, bad_id):
    root.mkdir()
    with pytest.raises(BackupError):
        get_backup(root, bad_id)


def test_missing_backup_id_raises(root):
    root.mkdir()
    with pytest.raises(BackupError):
        get_backup(root, "20990101-000000")


def test_no_backups_raises(root):
    with pytest.raises(BackupError):
        get_backup(root)
