# ⚙️[GenshinUID](https://github.com/KimigaiiWuyi/GenshinUID) Core 0.1.0

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Lint: flake8](https://img.shields.io/badge/lint-flake8-&labelColor=4C9C39)](https://flake8.pycqa.org/)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Genshin-bots/gsuid-core/master.svg)](https://results.pre-commit.ci/latest/github/Genshin-bots/gsuid-core/master)

[KimigaiiWuyi/GenshinUID](https://github.com/KimigaiiWuyi/GenshinUID) 的核心部分，平台无关，支持 HTTP/WS 形式调用，便于移植到其他平台以及框架。

目前仍在开发中。

## 安装Core

1. git clone gsuid-core本体

```shell
git clone https://ghproxy.com/https://github.com/Genshin-bots/gsuid-core.git --depth=1 --single-branch
```

2. 安装poetry

```shell
pip install poetry
```

3. 安装所需依赖

```shell
poetry install
```

4. 安装所需插件

```shell
# 安装v4 GenshinUID
cd plugins
git clone -b v4 https://ghproxy.com/https://github.com/KimigaiiWuyi/GenshinUID.git --depth=1 --single-branch
```

5. 启动gsuid-core

```shell
# 在gsuid_core/genshin_core文件夹内
poetry run python core.py
```

6. 链接其他适配端

+ 默认core将运行在`localhost:8765`端口上，如有需要可至`config.json`修改。
+ 在支持的Bot上（例如NoneBot2、HoshinoBot），安装相应适配插件，启动Bot（如果有修改端口，则需要在启动Bot前修改适配插件相应端口），即可自动连接Core端。

## Docker部署Core（可选）

`请先安装好Docker与Docker Compose`

1. git clone gsuid-core本体

```shell
git clone https://ghproxy.com/https://github.com/Genshin-bots/gsuid-core.git --depth=1 --single-branch
```

2. Docker Compose启动

```shell
cd gsuid-core
docker-compose up -d
```

- Docker Compose启动前，最好先安装需要的插件，如[GenshinUID](https://github.com/KimigaiiWuyi/GenshinUID)，这样容器在部署时可以一起安装依赖，节省时间
- 默认core将运行在`localhost:8765`端口上，Docker部署必须修改`config.json`，如`0.0.0.0:8765`
- 如果Bot（例如NoneBot2、HoshinoBot）也是Docker部署的，Core或其插件更新后，可能需要将Core和Bot的容器都重启才生效

## 编写插件


```python
import asyncio

from gsuid_core.sv import SL, SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event


@SV('开关').on_prefix(('关闭', '开启')) # 定义一组服务`开关`，服务内有两个前缀触发器
async def get_switch_msg(bot: Bot, ev: Event):
    name = ev.text         # 获取消息除了命令之外的文字
    command = ev.command   # 获取消息中的命令部分
    im = await process(name)  # 自己的业务逻辑
    await bot.logger.info('正在进行[关闭/开启开关]')  # 发送loger
    await bot.send(im)   # 发送消息

sv=SV(
    name='复杂的服务',  # 定义一组服务`开关`,
    pm=2, # 权限 0为master，1为superuser，2为群的群主&管理员，3为普通
    priority=5, # 整组服务的优先级
    enabled=True, # 是否启用
    black_list=[] # 黑名单
)

@sv.on_prefix('测试')
async def get_msg(bot: Bot, ev: Event):
    ...
```
