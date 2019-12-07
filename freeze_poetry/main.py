import os

from .package import Package


def main(root_dir: os.PathLike):
    pkg = Package(root_dir)

    return pkg
