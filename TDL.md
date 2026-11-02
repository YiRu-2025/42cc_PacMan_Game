一：项目内容
（一）：基础工程搭建与配置规范

- [x] .gitignore：忽略 __pycache__/、.mypy_cache/、venv/、build/、dist/、本地生成的高分文件。
- [x] Makefile：自动化脚本，编写 install、run、debug、clean、lint、lint-strict 规则；install 必须包含对方 A-Maze-ing 包的安装命令。
    - [ ] check alternative way for wildcard
- [x] requirements.txt：pygame、flake8、mypy、pyinstaller，以及被分配的 A-Maze-ing 包。
- [ ] pac-man.py：根目录入口脚本，只检查参数个数后调用 pacman.app.main()。
- [ ] pacman/ 骨架：建立空的包目录与 __init__.py，entities/ 与 scenes/ 子包。
- [x] project_management/timeline.md：甘特图或看板，六个阶段的计划起止时间。
    - [ ] missing time period setting
- [ ] project_management/analysis.md：技术选型说明，含 pygame 与 MLX 的函数对照表。
- [ ] project_management/risks.md：风险与缓解。
- [ ] project_management/team.md：分工记录，决策与争议的处理方式。

（二）数据层与外部包集成
- [ ] pacman/constants.py：默认值、颜色、格子像素大小、方向枚举。
- [ ] pacman/config.py：先剔除 # 注释行再 json.loads，输出 Config dataclass；逐键做类型与范围校验，非法值回退默认并打印提示，未知键忽略，全程不抛 traceback。
- [ ] config.json：带注释的默认配置模板，键名与 README 的 Configuration 节一一对应。
- [ ] pacman/maze_loader.py：MazeLoader.generate(width, height, seed) -> Grid，PERFECT=False，try/except 包住对方包的全部调用；加载后计算可到达格子集合，排除封闭的 "42" 图案区域。
- [ ] tests/test_config.py、tests/test_maze_loader.py。

（三）核心对局逻辑
- [ ] pacman/level.py：在可到达格子铺豆子，四角放超级豆与幽灵出生点；玩家出生点取离几何中心最近的可到达格子。
- [ ] pacman/entities/base.py：实体基类，网格坐标、朝向、移动步进。
- [ ] pacman/entities/player.py：撞墙检测、转向缓冲、吃豆判定。
- [ ] pacman/entities/ghost.py：CHASE / FRIGHTENED / DEAD 三态机，追逐用 BFS 取下一步，逃跑选离玩家最远的邻格，被吃后计时返回自己的角落重生。
- [ ] pacman/game.py：分数只增不减，生命与分数跨关保留，第 1 关固定种子、之后随机，关卡计时与超时处理。
- [ ] tests/test_level.py、test_ghost.py、test_game.py（A）。
本阶段结束时与敲定 Config、Grid、以及一局结束的结果对象三个接口。

（四）图形与界面
- [ ] pacman/gfx.py：唯一接触 pygame 的模块，封装窗口、贴图、文字、事件轮询、帧率；其他模块一律不 import pygame。
- [ ] pacman/renderer.py：格子坐标转像素，绘制墙体图块、豆子、实体与 HUD（分数、生命、关卡、剩余时间）。
- [ ] pacman/scenes/base.py：Scene 接口 handle_key / update / draw。
- [ ] pacman/scenes/play.py：对局场景。
- [ ] pacman/app.py：场景管理器与主循环。
- [ ] pacman/scenes/menu.py、instructions.py、scores.py、pause.py（B）：主菜单（开始、高分、说明、退出）、暂停菜单（继续、回主菜单）。
- [ ] assets/

（五）高分与作弊
- [ ] pacman/highscores.py：容忍文件缺失或损坏，名字限 10 字符且仅字母数字与空格，保留前十，写入用 with。
- [ ] pacman/scenes/name_entry.py：兼作胜利与失败结算画面，显示最终分数并接入保存。
- [ ] pacman/cheats.py：无敌、跳关、冻结幽灵、加命、加速，按键写入说明页；跳关优先级最高。
- [ ] tests/test_highscores.py。

（六）收尾与发布
- [ ] pacman.spec（B）：PyInstaller 规格，打包 assets/、默认配置与说明文件；用 sys._MEIPASS 处理资源路径，上传 itch.io 设为未公开，并练习现场重新打包。
- [ ] README.md（各写各的模块）：首行斜体署名，含 Description、Instructions、Resources（含 AI 使用说明）、Configuration、Highscore、Maze Generation、Implementation、General Software、Architecture、Project Management，全英文。
- [ ] project_management/progress.md：实际进度对比计划。
- [ ] project_management/test_plan.md：验收测试项、发现与修复的 bug。
- [ ] project_management/issues.md：阻塞点与分歧记录。

