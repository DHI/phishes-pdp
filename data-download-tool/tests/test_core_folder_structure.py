import json

from src.core.folder_structure import PDPFolderStructure, create_pdp_folders


def test_create_structure_and_metadata(tmp_path):
    manager = PDPFolderStructure(base_path=tmp_path)
    out = manager.create_structure()

    assert out == tmp_path
    assert (tmp_path / "logs").exists()
    assert (tmp_path / "logs" / "README.md").exists()
    metadata = json.loads((tmp_path / ".pdp_metadata.json").read_text(encoding="utf-8"))
    assert metadata["project_name"] == "PHISHES Digital Platform Project"


def test_get_dataset_path(tmp_path):
    manager = PDPFolderStructure(base_path=tmp_path)
    path = manager.get_dataset_path("climate", "precipitation")
    assert path == tmp_path / "data" / "climate" / "precipitation"


def test_list_and_verify_structure(tmp_path):
    structure = {"a": {"b": {}}, "logs": {}}
    manager = PDPFolderStructure(base_path=tmp_path, custom_structure=structure)
    manager.create_structure()

    listed = manager.list_structure()
    listed_normalized = {path.replace("\\", "/") for path in listed}
    assert (
        "a" in listed_normalized
        and "a/b" in listed_normalized
        and "logs" in listed_normalized
    )

    verified = manager.verify_structure()
    verified_normalized = {
        key.replace("\\", "/"): value for key, value in verified.items()
    }
    assert verified_normalized["a"] is True
    assert verified_normalized["a/b"] is True
    assert verified_normalized["logs"] is True


def test_create_pdp_folders_convenience(tmp_path):
    out = create_pdp_folders(base_path=tmp_path)
    assert out == tmp_path
    assert (tmp_path / "logs").exists()
