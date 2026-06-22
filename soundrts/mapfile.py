import io
import os.path
import re
from hashlib import sha256
from zipfile import ZipFile

from .lib.package import ZipPackage, Package, resource_layer, FolderPackage
from .lib.log import warning
from .lib import zipdir


def _name_from_path(path):
    """从打包名/路径得到逻辑地图 id。

    合作战役章节使用 ``战役名/章节号``（可含 ``/``）；须保留该前缀供客户端
    加载战役 ui/tts.txt。单文件名地图仍走 basename 并去掉非法字符。
    """
    path = path.replace("\\", "/")
    for ext in (".txt", ".zip", ".pkg"):
        if path.lower().endswith(ext):
            path = path[: -len(ext)]
            break
    if "/" in path:
        return path
    name = os.path.basename(path)
    name = re.sub(r'[\\:*?"<>|]', "", name)
    return name


class Map:
    # stats, logs, replay menu... (not really an id though)
    name = "unknown"

    # raw content
    buffer: bytes = None
    buffer_name: str = None  # includes the extension for the filetype (check if zipfile?)

    # unpacked content
    definition: str = None
    resources = None

    # header (also in parsed definition)
    title: list
    nb_players_min: int
    nb_players_max: int

    def __init__(self, path: str = None):
        if path is not None:
            self._init_from_path(path)

    @staticmethod
    def load(f, name):
        m = Map()
        # 检查f是否是文件对象，如果是，则加载字节数据
        if hasattr(f, 'read'):
            m._init_from_buffer(f.read(), name)
        # 如果f是字符串路径，且是文件夹，则直接加载文件夹
        elif isinstance(f, str) and os.path.isdir(f):
            m._init_from_dir(f, name)
        # 如果f是Package类型对象，则使用package对象加载
        elif isinstance(f, Package):
            m.name = _name_from_path(name)
            m.buffer_name = name  # 确保buffer_name被设置
            m._load_from_package(f)
        return m

    def _load_from_text_file(self, f):
        try:
            self.definition = f.read()
            self._load_header()
        except Exception as e:
            warning(f"加载地图文本文件失败: {e}")
            raise

    def _load_from_package(self, package):
        try:
            self.resources = resource_layer(package, self.name)
            # 确保buffer_name被设置
            if self.buffer_name is None:
                self.buffer_name = self.name
            # 检查map.txt是否存在
            if not self.resources.isfile("map.txt"):
                warning(f"地图文件夹中找不到map.txt文件: {self.name}")
                raise FileNotFoundError(f"Map.txt not found in {self.name}")
                
            self._load_from_text_file(self.resources.open_text("map.txt"))
            
            # 对于文件夹地图，创建包含所有资源的ZIP缓冲区以供网络传输
            if self.buffer is None:
                self._create_zip_buffer_from_package(package)
                
        except Exception as e:
            warning(f"从包加载地图失败: {e}")
            raise

    def _create_zip_buffer_from_package(self, package):
        """为文件夹地图创建ZIP格式的缓冲区，包含所有资源文件"""
        try:
            # FolderPackage继承自str，直接是路径字符串
            package_path = str(package)
            if os.path.isdir(package_path):
                zip_io = io.BytesIO()
                zipdir.zipdir(package_path, zip_io)
                self.buffer = zip_io.getvalue()
                # 确保buffer_name不以.txt结尾，让客户端按ZIP处理
                if self.buffer_name and self.buffer_name.endswith('.txt'):
                    self.buffer_name = self.buffer_name[:-4]  # 移除.txt后缀
            else:
                # 如果无法直接访问文件夹，创建包含map.txt的文本缓冲区作为后备
                if hasattr(self, 'definition') and self.definition:
                    self.buffer = self.definition.encode("utf-8", errors="replace")
                    # 设置为.txt格式让客户端按文本处理
                    if self.buffer_name and not self.buffer_name.endswith('.txt'):
                        self.buffer_name = self.buffer_name + '.txt'
        except Exception as e:
            warning(f"创建ZIP缓冲区失败: {e}")
            # 后备方案：创建文本缓冲区
            if hasattr(self, 'definition') and self.definition:
                self.buffer = self.definition.encode("utf-8", errors="replace")
                # 设置为.txt格式让客户端按文本处理
                if self.buffer_name and not self.buffer_name.endswith('.txt'):
                    self.buffer_name = self.buffer_name + '.txt'

    def _init_from_path(self, path):
        self.name = _name_from_path(path)
        # 确保buffer_name被设置为路径的basename
        self.buffer_name = os.path.basename(path)
        if path.endswith(".txt"):
            f = open(path, encoding="utf-8", errors="replace")
            self._load_from_text_file(f)
            # 对于.txt文件，生成缓冲区以供网络传输
            if self.buffer is None and hasattr(self, 'definition') and self.definition:
                self.buffer = self.definition.encode("utf-8", errors="replace")
        elif os.path.isdir(path):
            # 直接加载文件夹
            self._init_from_dir(path, os.path.basename(path))
        else:
            package = Package.from_path(path)
            self._load_from_package(package)
    
    def _init_from_dir(self, dir_path, name):
        """处理文件夹类型的地图"""
        self.name = _name_from_path(name)
        
        # 检查目录中是否有map.txt文件
        map_txt_path = os.path.join(dir_path, "map.txt")
            
        package = FolderPackage(dir_path)
        self._load_from_package(package)

    @staticmethod
    def loads(buffer: bytes, name):
        map_ = Map()
        map_._init_from_buffer(buffer, name)
        return map_

    def _init_from_buffer(self, buffer, name_with_ext):
        self.buffer = buffer
        self.buffer_name = name_with_ext
        path = name_with_ext  # "short path" (Path.name)
        self.name = _name_from_path(path)
        if path.endswith(".txt"):
            s = buffer.decode(encoding="utf-8", errors="replace")
            f = io.StringIO(s, newline=None)
            self._load_from_text_file(f)
        else:
            package = ZipPackage(ZipFile(io.BytesIO(buffer)))
            self._load_from_package(package)

    def _load_header(self):
        self.title = self._extract_title()
        self.nb_players_min = self._find_int_from("nb_players_min", 1)
        self.nb_players_max = self._find_int_from("nb_players_max", 1)

    def _extract_title(self):
        return [f"{self.name}"] + self._title_from_definition()

    def _title_from_definition(self) -> list:
        line: str = self._find_a_line_with("title")
        if line:
            # 检查并处理等号格式的标题（如"title = 123"）
            if "=" in line:
                # 去掉等号及其前后的空格
                line = line.replace("=", " ").strip()
                
            # 支持数字ID和文本标题
            parts = []
            for part in line.split(" "):
                if not part:  # 跳过空字符串
                    continue
                try:
                    parts.append(int(part))
                except ValueError:
                    # 如果不是数字，则作为字符串添加
                    parts.append(part)
            return parts
        else:
            return []

    def _find_a_line_with(self, keyword):
        # 修改正则表达式以匹配任何字符，而不仅仅是数字
        match = re.search("(?m)^%s[ \t]+(.+)$" % keyword, self.definition)
        if match:
            return match.group(1)

    def _find_int_from(self, keyword, default):
        line = self._find_a_line_with(keyword)
        if line:
            return int(line)
        else:
            return default

    def digest(self):
        # 对于文件夹类型的地图，如果没有buffer，则使用地图名称和definition内容生成摘要
        if self.buffer is None:
            if self.definition is not None:
                data = (self.name + self.definition).encode('utf-8')
                return sha256(data).hexdigest()
            else:
                # 如果既没有buffer也没有definition，则使用地图名称生成摘要
                return sha256(self.name.encode('utf-8')).hexdigest()
        else:
            return sha256(self.buffer).hexdigest()
