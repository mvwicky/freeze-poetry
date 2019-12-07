from typing import Dict, List

import attr

FileMeta = Dict[str, str]
FileMetaList = List[FileMeta]


def fmt_hash(pkg_hash: str, indent: int = 4) -> str:
    spaces = " " * indent
    return f"{spaces}--hash={pkg_hash}"


@attr.s(slots=True, auto_attribs=True)
class Dependency(object):
    name: str
    version: str
    hashes: List[str] = attr.ib(factory=list, repr=False)
    marker: str = attr.ib(default="", repr=False)
    dependencies: List[str] = attr.ib(factory=list)

    @classmethod
    def from_lock(cls, elem: Dict[str, str], metadata: FileMetaList) -> "Dependency":
        name = elem["name"]
        version = elem["version"]
        marker = elem.get("marker", "")
        if "extra == " in marker:
            marker = ""
        dependencies = list(elem.get("dependencies", {}).keys())
        hashes = [e["hash"] for e in metadata]
        return cls(
            name=name,
            version=version,
            hashes=hashes,
            marker=marker,
            dependencies=dependencies,
        )

    def to_line(self, indent: int = 4, with_hash: bool = True) -> str:
        init_line = f"{self.name}=={self.version}"
        if self.marker:
            init_line = "; ".join([init_line, self.marker])
        if with_hash:
            init_line = " ".join([init_line, "\\"])
        line = [init_line]
        if with_hash:
            line.extend([fmt_hash(h, indent) + " \\" for h in self.hashes[:-1]])
            line.append(fmt_hash(self.hashes[-1], indent))
        return "\n".join(line)
