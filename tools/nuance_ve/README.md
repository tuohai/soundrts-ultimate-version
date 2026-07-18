# Nuance Vocalizer helper（SoundRTS 本地苹果音库）

32 位 Java 助手：加载 **本游戏** `user/voices/nuance/vl` 里的 `ve.dll`。

## 安装音库（推荐）

在游戏里：**选项 → 游戏语音 → 导入苹果音库到本游戏**

会把迷雾世界的 `vl` + 32 位 `jre` **复制到**：

```
user/voices/nuance/vl/
user/voices/nuance/jre/
```

之后运行时只读上述目录，**不再指向迷雾世界**。

## 重建助手 JAR

```bat
javac -encoding UTF-8 -source 1.7 -target 1.7 -cp lib\jna.jar -d out src\soundrts\nuance\*.java
jar cfm nuance_ve_helper.jar out\manifest.txt -C out soundrts
copy /Y lib\jna.jar jna.jar
```

## 打包注意

发行包需带上本目录的两个 jar（放在可执行文件旁的 ``tools/nuance_ve/``）。
``build_game.py`` 会自动拷贝。仅有 ``user/voices/nuance`` 音库不够——还要能找到 helper。

开发时 jar 放在仓库 ``tools/nuance_ve`` 即可；运行时也会在 ``user/voices/nuance/helper`` 查找（导入音库时会复制一份）。

## 授权

音库与 DLL 来自你已拥有的迷雾世界拷贝；请勿再分发 `user/voices/nuance`。
