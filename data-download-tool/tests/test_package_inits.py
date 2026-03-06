import src.analysis as analysis
import src.core as core
import pytest


def test_analysis_exports():
    assert "compute_anomalies" in analysis.__all__
    assert callable(analysis.compute_anomalies)


def test_core_dir_and_getattr():
    names = core.__dir__()
    assert "PDPDataDownloader" in names
    assert core.__getattr__("PDPDataDownloader") is not None


def test_core_getattr_unknown_raises():
    with pytest.raises(AttributeError):
        core.__getattr__("does_not_exist")
