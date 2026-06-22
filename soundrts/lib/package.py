import io
import os
import re
import zipfile
from pathlib import Path
from typing import IO
from zipfile import ZipFile

from soundrts.lib import encoding
from soundrts.lib.zipdir import zipdir


class Package:  # Dir? VirtualDir?
    """a (virtual) directory (actually in a filesystem or in a zip file)"""
    name = "default"

    @staticmethod
    def from_path(name: str):
        name = Path(name)
        if name.suffix in [".zip", ".pkg"]:
            return ZipPackage(ZipFile(name))
        else:
            return FolderPackage(name)

    def open_binary(self, name) -> IO: ...
    def dirnames(self): ...
    def filenames(self): ...
    def relative_paths_of_files_in_subtree(self, subdir): ...
    def subpackage(self, subdir): ...

    def open_text(self, name):
        b = self.open_binary(name)
        try:
            raw = b.read()
        finally:
            b.close()
        if encoding.is_tts_file(name):
            # tts 必须严格解码；errors=replace 会把坏字节变成 U+FFFD，再被编辑器存盘即永久乱码。
            return io.StringIO(encoding.decode_tts_bytes(raw, name))
        enc = encoding.encoding(raw, name)
        try:
            text = raw.decode(enc, errors="strict")
        except UnicodeDecodeError as err:
            # 非 tts 的遗留资源文件（例如某些第三方 mod 的 rules.txt / ai.txt）
            # 可能是 cp1252 / latin-1 编码却没有声明 `; coding:`，其中注释或单位名
            # 里的重音字符（如 0xe9 = 'é'）会让严格 UTF-8 解码失败。为避免整个游戏
            # 在启动时因一个 mod 的编码问题而崩溃，这里回退到 cp1252 容错解码并告警。
            # （tts 仍走上面的严格分支，不受影响，避免静默损坏译文。）
            from .log import warning
            warning(
                "failed to decode %s as %s (%s); falling back to cp1252. "
                "Add '; coding: utf-8' on line 1 and re-save as UTF-8 to silence this.",
                name, enc, err,
            )
            text = raw.decode("cp1252", errors="replace")
        return io.StringIO(text)

    def isfile(self, name): ...
    def isdir(self, name): ...
    
    def has_file(self, path):
        """检查指定路径的文件是否存在
        
        Args:
            path: 文件路径
            
        Returns:
            bool: 文件是否存在
        """
        try:
            return self.isfile(path)
        except:
            return False

    def is_a_soundpack(self):
        for name in ("rules.txt", "ai.txt"):
            if self.isfile(name):
                return False
        return True


class FolderPackage(str, Package):  # DirInFilesystem?

    def open_binary(self, name):
        path = os.path.join(self, name)
        # local folder reading by zipping the folder first
        if os.path.isdir(path):
            f = io.BytesIO()
            zipdir(path, f, compression=zipfile.ZIP_STORED)
            f.seek(0)
            return f
        return open(path, "rb")

    def isfile(self, name):
        path = os.path.join(self, name)
        return os.path.isfile(path)

    def isdir(self, name):
        path = os.path.join(self, name)
        return os.path.isdir(path)

    def dirnames(self):
        return next(os.walk(self))[1]

    def filenames(self):
        return next(os.walk(self))[2]

    def relative_paths_of_files_in_subtree(self, subdir):
        top = os.path.join(self, subdir)
        if os.path.isdir(top):
            for dirpath, _, filenames in os.walk(top):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    yield path[len(self)+1:]

    def subpackage(self, subdir):
        path = os.path.join(self, subdir)
        if os.path.isdir(path):
            return Package.from_path(path)


class ZipPackage(Package):  # DirInZip?
    def __init__(self, zipfile: ZipFile, subdir: str = None):
        self._zipfile = zipfile
        self._subdir = subdir

    def __repr__(self):
        if self._subdir is None:
            return f"<ZipPackage filename='{self._zipfile.filename}'>"
        else:
            return f"<ZipPackage filename='{self._zipfile.filename}' subdir='{self._subdir}'>"

    def dirnames(self):
        result = set()
        for name in self._namelist():
            try:
                name = Path(name).parts[0]
            except IndexError:
                pass
            else:
                if not self.isfile(name):
                    result.add(name)
        return result

    def filenames(self):
        result = set()
        for name in self._namelist():
            try:
                name = Path(name).parts[0]
            except IndexError:
                pass
            else:
                if self.isfile(name):
                    result.add(name)
        return result

    def relative_paths_of_files_in_subtree(self, path):
        for name in self._namelist():
            if name.startswith(path + "/"):
                yield name

    def subpackage(self, subdir):
        if subdir.endswith(".zip") and subdir in self._namelist():
            return ZipPackage(ZipFile(self.open_binary(subdir)))
        for name in self._namelist():
            if name.startswith(subdir + "/"):
                return ZipPackage(self._zipfile, self._path(subdir))

    def open_binary(self, name):
        return self._zipfile.open(self._path(name))

    def _path(self, name):
        if not self._subdir:
            return name
        else:
            return self._subdir + "/" + name

    def isfile(self, name):
        return self._path(name) in self._zipfile.namelist()

    def isdir(self, name):
        for n in self._namelist():
            if n.startswith(name + "/"):
                return True

    def _namelist(self):
        if self._subdir is None:
            return self._zipfile.namelist()
        else:
            return self._short_name_list()

    def _short_name_list(self):
        start = self._subdir + "/"
        for name in self._zipfile.namelist():
            if name.startswith(start):
                yield name[len(start):]


def resource_layer(package, name):
    if package:
        package.name = name
    return package


def _load_mod_metadata(mod):
    """Parse mod.txt: optional ``mods`` dependencies and ``title`` for the mod menu."""
    if not mod.isfile("mod.txt"):
        return
    with mod.open_text("mod.txt") as f:
        s = f.read()
    m = re.search("(?m)^mods[ \t]+(.+)$", s)
    if m:
        mod.mods = [x.strip() for x in m.group(1).split(",") if x.strip()]
    elif s.startswith("mods "):
        mod.mods = [x.strip() for x in s.split(" ", 1)[1].strip().split(",") if x.strip()]
    m = re.search("(?m)^title[ \t]+(.+)$", s)
    if m:
        # split() 而非 split(" ")：Windows CRLF 会在末 token 上留下 \r，导致 TTS 查不到 ID
        mod.menu_title = m.group(1).split()


def mod_menu_label(packages, mod_name):
    """Return voice-menu tokens for a mod (TTS IDs, words, or folder name)."""
    mod = packages.mod(mod_name)
    if mod is not None and getattr(mod, "menu_title", None):
        return mod.menu_title
    return [mod_name]


class PackageStack(list):
    def __init__(self, paths):
        list.__init__(self)
        self.extend(map(Package.from_path, paths))

    def mod(self, name):
        for package in reversed(self):
            subdir = "mods/" + name
            mod = resource_layer(package.subpackage(subdir), name)
            if mod:
                _load_mod_metadata(mod)
                return mod

    def mods(self):
        mod_names = set()
        for package in reversed(self):
            subdir = "mods"
            mods = package.subpackage(subdir)
            if mods is not None:
                mod_names.update(mods.dirnames())
        return [self.mod(name) for name in mod_names]
