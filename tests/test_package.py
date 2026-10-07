"""Installation contract; must pass without adding src to the import path."""

from importlib import import_module, metadata, resources


def test_installed_package_exposes_matching_version() -> None:
    package = import_module("finance_toolkit")
    assert package.__version__ == metadata.version("finance-toolkit")


def test_package_ships_typing_marker() -> None:
    assert resources.files("finance_toolkit").joinpath("py.typed").is_file()
