import json
import logging
import os
import shutil
import subprocess
from functools import partialmethod
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import attr
import toml

from .dependency import Dependency

logger = logging.getLogger(__name__)

CWD = Path.cwd()


@attr.s(slots=True, auto_attribs=True, repr=False)
class Package(object):
    root_dir: os.PathLike = attr.ib(default=CWD, converter=Path)
    log_name: Optional[str] = None
    dev: bool = attr.ib(default=False, kw_only=True)
    req_file: Path = attr.ib(kw_only=True)
    dev_file: Path = attr.ib(kw_only=True)
    lock_file: Path = attr.ib(kw_only=True)
    node_package: Path = attr.ib(kw_only=True)
    prettier_exe: Path = attr.ib(repr=False, init=False)
    pyproject: Path = attr.ib(repr=False, init=False)
    version_file: Path = attr.ib(repr=False, init=False)
    _logger: logging.Logger = attr.ib(init=False)

    @req_file.default
    def _req_default(self):
        return self.root_dir / "requirements.txt"

    @dev_file.default
    def _dev_default(self):
        return self.root_dir / "requirements-dev.txt"

    @lock_file.default
    def _lock_default(self):
        return self.root_dir / "poetry.lock"

    @node_package.default
    def _pkg_default(self):
        return self.root_dir / "package.json"

    @prettier_exe.default
    def _prettier_default(self):
        node_bin = self.root_dir / "node_modules" / ".bin"
        prettier_exe = node_bin / "prettier"
        if prettier_exe.is_file():
            return str(prettier_exe)
        else:
            return shutil.which("prettier")

    @pyproject.default
    def _proj_default(self):
        return self.root_dir / "pyproject.toml"

    @version_file.default
    def _ver_default(self):
        return self.root_dir / "sell" / "__version__.py"

    @_logger.default
    def _log_default(self):
        return logging.getLogger(self.log_name)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any):
        self._logger.log(level, msg, *args, **kwargs)

    debug = partialmethod(log, logging.DEBUG)
    info = partialmethod(log, logging.INFO)
    warning = partialmethod(log, logging.WARNING)
    error = partialmethod(log, logging.ERROR)
    critical = partialmethod(log, logging.CRITICAL)

    def __repr__(self):
        return f"<Package: {self.root_dir}>"

    def sh(self, args, **kwargs):
        cmd = args
        if not isinstance(cmd, str) and isinstance(cmd, Sequence):
            cmd = " ".join(cmd)
        self.debug("Running command: `{0}`".format(cmd))
        return subprocess.run(args, **kwargs)

    def read_pyproject(self):
        return toml.loads(self.pyproject.read_text())

    def read_node_package(self):
        return json.loads(self.node_package.read_text())

    def read_lock(self):
        self.debug("Reading lock file: %s", self.lock_file)
        return toml.loads(self.lock_file.read_text())

    def get_dependencies(self) -> Iterable[Dependency]:
        lock_data = self.read_lock()
        file_meta = lock_data["metadata"]["files"]
        for elem in lock_data["package"]:
            if self.dev or elem["category"] != "dev":
                name = elem["name"]
                yield Dependency.from_lock(elem, file_meta[name])

    def poetry_update(self):  # pragma: no cover
        self.sh(["poetry", "update"], check=True)

    def make_requirements(self):
        self.debug("Constructing requrements")
        frozen_pkgs = []
        for dep in self.get_dependencies():  # type: Dependency
            frozen_pkgs.append(dep.to_line())
        logger.debug("%d requirements", len(frozen_pkgs))
        req = "\n".join(frozen_pkgs) + "\n"
        return req, len(frozen_pkgs)

    def freeze(self, force_update: bool = False):
        if force_update or not self.lock_file.is_file():  # pragma: no cover
            self.debug("Updating.")
            self.poetry_update()

        req_cts, num_pkgs = self.make_requirements()
        file = self.req_file if not self.dev else self.dev_file
        self.debug("Freezing requirements: %s", file)
        write = not file.is_file() or req_cts != file.read_text()
        if write:
            self.debug("Writing new %s", file.name)
            file.write_text(req_cts)
        else:
            logger.debug("%s unchanged", file.name)
        self.debug(f"Froze {num_pkgs} requirements ({file})")
        return write

    def version_bump(self):
        self.sh(["poetry", "version", "patch"])
        self.sh(["yarn", "version", "--patch", "--no-git-tag-version"])
        return self.version_sync()

    def make_tag(self):
        version = self.version_sync()
        tag = "v" + version
        self.sh(["git", "tag", tag])

    def pyproj_version(self):
        pyproject = self.read_pyproject()
        return pyproject["tool"]["poetry"]["version"]

    def version_sync(self):
        self.debug("Syncing versions in pyproject.toml and package.json")
        node_pkg = self.read_node_package()
        version = self.pyproj_version()
        if node_pkg["version"] != version:
            self._prettier(json.dumps(node_pkg), self.node_package)
        return version

    def _prettier(self, data: str, json_file: Path):
        if self.prettier_exe is not None:
            self.debug("Running output through prettier.")
            args = [self.prettier_exe, "--parser", "json"]
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(data, timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                self.stderr.write(stderr)
                json_file.write_text(data)
            else:
                json_file.write_text(stdout)
        else:
            json_file.write_text(data)
