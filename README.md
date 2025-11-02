# 一夜狼人杀（Python 实现）

一个用 Python 实现的「一夜狼人杀」游戏，提供两种游戏模式：
- **CLI 热座版**：适合真人玩家面对面游戏
- **LLM 自动版**：使用大语言模型自动模拟玩家，适合演示和学习

支持完整的游戏流程：准备阶段、夜晚行动、讨论阶段、投票阶段和自动结算。

## 功能特点

### 核心功能
- **6人固定配置**：包含9张角色牌（场上6张 + 中央3张）
- **完整游戏流程**：准备 → 夜晚行动 → 讨论阶段 → 投票 → 结算
- **夜晚行动**：按官方顺序执行（狼人、爪牙、预言家、强盗、捣蛋鬼、酒鬼、失眠者）
- **自动结算**：根据票型与角色规则判断出局与胜负（包含猎人被处决的连带效果）
- **角色系统**：支持所有6人入门配置角色及其特殊技能

### CLI 热座版特点
- **保密交互**：私密输入与热座提示，避免泄露信息
- **讨论计时器**：可配置倒计时，支持跳过
- **可选夜间日志**：结算后可展示夜间行动摘要

### LLM 自动版特点
- **AI 玩家**：使用 LangChain + OpenAI 自动模拟玩家行为
- **智能发言**：每个角色根据专属 Prompt 生成策略性发言
- **自动夜晚行动**：AI 根据角色技能自动选择合适的行动
- **可配置模型**：支持 OpenAI 兼容的 API（通过环境变量配置）

## 目录结构

```
Werewolves/
  README.md              # 使用说明（本文件）
  werewolves_cli.py      # CLI 热座版入口
  werewolves_llm.py      # LLM 自动版入口
  game_engine.py         # 游戏引擎与玩家类
  roles.py               # 角色与夜晚行动实现
  role_prompts.py        # 角色专属 Prompt 模板（LLM 版）
  llm_agents.py          # LLM Agent 系统（LLM 版）
  lc_tools.py            # LangChain 工具封装（LLM 版）
  resolver.py            # 投票统计与胜负判定
  ui.py                  # 交互式命令行 UI（CLI 版）
  一夜狼人杀规则.txt        # 规则参考（中文）
```

## 安装要求

### 基础要求
- Python 3.8+

### CLI 热座版
- **无需额外依赖**：纯标准库实现

### LLM 自动版
需要安装以下依赖：
```bash
pip install langchain-openai langchain python-dotenv
```

## 快速开始

### CLI 热座版

适合真人玩家面对面游戏，通过热座模式轮流操作：

```bash
python werewolves_cli.py --names "Alice,Bob,Carol,David,Eve,Frank" --timer 180 --reveal-log
```

**命令行参数：**
- `--names`：6名玩家名，逗号分隔。默认 `P1,P2,P3,P4,P5,P6`
- `--seed`：随机种子（整数）。用于复现实验或教学演示
- `--timer`：讨论时长（秒）。默认 180
- `--reveal-log`：结算后展示夜间行动日志的开关（布尔旗标）

**示例：**
```bash
# 使用固定玩家名、120秒讨论、展示夜间日志
python werewolves_cli.py --names "Alice,Bob,Carol,David,Eve,Frank" --timer 120 --reveal-log

# 为了复现实验，设定随机种子
python werewolves_cli.py --seed 42
```

### LLM 自动版

使用大语言模型自动模拟所有玩家，适合演示和学习：

**1. 配置环境变量**

创建 `.env` 文件（或设置环境变量）：
```bash
# OpenAI API 配置
API_KEY=your-api-key-here
BASE_URL=https://api.openai.com/v1  # 或你的自定义 API 地址
MODEL_NAME=gpt-4o-mini              # 模型名称
```

**2. 运行游戏**

```bash
python werewolves_llm.py --names "P1,P2,P3,P4,P5,P6" --speech-rounds 2 --reveal-log
```

**命令行参数：**
- `--names`：6名玩家名，逗号分隔。默认 `P1,P2,P3,P4,P5,P6`
- `--seed`：随机种子（整数）。用于复现实验
- `--speech-rounds`：发言轮数。默认 2
- `--reveal-log`：结算后展示夜间行动日志的开关（布尔旗标）

**示例：**
```bash
# 使用默认配置运行
python werewolves_llm.py

# 3轮发言，展示日志
python werewolves_llm.py --speech-rounds 3 --reveal-log

# 使用固定随机种子复现
python werewolves_llm.py --seed 12345
```

## 游戏流程概览

1. **准备阶段**（setup）
   - 从 9 张预设角色中洗牌，发给 6 名玩家；剩余 3 张置于中央
   - 每位玩家私下确认初始身份

2. **夜晚阶段**（night）
   - 按顺序依次唤醒拥有对应角色的玩家执行行动：
     - 狼人（Werewolf）
     - 爪牙（Minion）
     - 预言家（Seer）
     - 强盗（Robber）
     - 捣蛋鬼（Troublemaker）
     - 酒鬼（Drunk）
     - 失眠者（Insomniac）

3. **讨论阶段**（discussion）
   - **CLI 版**：公共讨论，计时器显示剩余时间；按回车可直接跳过
   - **LLM 版**：AI 玩家自动生成策略性发言，可配置多轮

4. **投票阶段**（voting）
   - **CLI 版**：热座保密逐人投票，不能投自己
   - **LLM 版**：AI 玩家根据游戏情况自动投票

5. **结算**
   - 统计最高票出局（全员一票则无人死亡）
   - 若猎人（Hunter）被处决，所有投给猎人的玩家也出局
   - 根据场上是否有狼人/爪牙与死亡情况判定胜负

## 角色与行动（入门 6 人配置）

预设 9 张角色牌：

- **狼人 Werewolf ×2**
  - 多狼互认；若独狼，可查看一张中央牌
- **爪牙 Minion ×1**
  - 知道所有狼人的身份；若无狼人，爪牙单挑局的胜负条件不同
- **预言家 Seer ×1**
  - 可选择查看一名玩家身份，或查看两张中央牌
- **强盗 Robber ×1**
  - 可与一名玩家交换身份，并得知自己新身份（可不交换）
- **捣蛋鬼 Troublemaker ×1**
  - 可选择两名玩家互换身份（自己不看、不变）
- **酒鬼 Drunk ×1**
  - 必须与中央一张牌交换，但不会得知新身份
- **失眠者 Insomniac ×1**
  - 夜晚最后查看自己的最终身份
- **猎人 Hunter ×1**
  - 白天若被处决，则所有投给猎人的玩家也出局

## 胜负判定（简述）

- **若场上有狼人：**
  - 被处决者中包含狼人 → **好人胜**
  - 无人被处决 → **狼人胜**
  - 被处决者中没有狼人（但有人出局）→ **狼人胜**

- **若场上无狼人：**
  - **有爪牙：**
    - 爪牙被处决 → **好人胜**
    - 其他任意人被处决（有人出局）→ **狼人阵营胜（爪牙胜）**
    - 无人出局 → **好人胜**
  - **无爪牙：**
    - 无人出局 → **好人胜**；有人出局 → **狼人阵营胜（好人失败）**

> 详见 `resolver.py` 中的判定逻辑。

## LLM 自动版架构说明

### Agent 系统

- **AgentPlayer 类**：绑定 Player 与 LLM
  - `execute_night_action()`：夜晚阶段根据角色绑定对应工具，让 LLM 执行
  - `generate_speech()`：白天阶段根据角色 Prompt 生成发言
  - `cast_vote_by_llm()`：让 LLM 决定投票目标

- **LLMAgentManager 类**：管理所有 AI 玩家
  - `execute_night_phase()`：按夜晚顺序执行各角色行动
  - `discussion_phase()`：控制多轮发言
  - `voting_phase()`：收集所有玩家投票

### 夜晚工具绑定

每个角色在夜晚阶段会自动绑定对应的 LangChain Tool：
- 狼人：`night_werewolf_tool`
- 爪牙：`night_minion_tool`
- 预言家：`night_seer_inspect_player_tool`, `night_seer_inspect_centers_tool`
- 强盗：`night_robber_swap_tool`, `night_robber_skip_tool`
- 捣蛋鬼：`night_troublemaker_swap_tool`
- 酒鬼：`night_drunk_swap_tool`
- 失眠者：`night_insomniac_check_tool`

### 角色 Prompt 系统

每个角色都有专属的系统 Prompt（`role_prompts.py`），包含：
- 角色背景和阵营归属
- 策略要点和发言风格
- 动态注入的游戏上下文（初始身份、当前身份、历史发言等）

## 操作提示

### CLI 热座版
- 夜晚阶段与投票阶段均采用「仅当前玩家可见」的屏幕提示
- 传递键盘前请先清屏，程序会自动清屏并标注当前可见者
- 讨论阶段按回车可跳过计时

### LLM 自动版
- 所有操作自动执行，无需人工干预
- 可以观察 AI 玩家的决策过程和发言内容
- 适合用于游戏规则学习和策略研究

## 开发与扩展

### 核心模块
- **引擎入口**：`werewolves_cli.py`（CLI 版）、`werewolves_llm.py`（LLM 版）
- **游戏核心**：`game_engine.py`（玩家、阶段流转、日志）
- **角色行动**：`roles.py`（继承 `RoleAction` 并在 `ROLE_ACTIONS` 注册）
- **结算规则**：`resolver.py`
- **UI 交互**：`ui.py`（CLI 版）
- **LLM 集成**：`llm_agents.py`、`lc_tools.py`、`role_prompts.py`（LLM 版）

### 扩展方式

- **新增角色**：
  1. 在 `roles.py` 中定义 `Role` 枚举项
  2. 创建对应的 `RoleAction` 子类并加入 `ROLE_ACTIONS`
  3. 将角色加入 `GameEngine.NIGHT_ORDER`（如有夜晚行动）
  4. 在 `llm_agents.py` 中添加夜晚工具映射（LLM 版）
  5. 在 `role_prompts.py` 中添加角色 Prompt（LLM 版）
  6. 更新角色配置池 `GameEngine.SIX_PLAYER_STARTER_ROLES`

- **修改配置**：调整 `GameEngine.SIX_PLAYER_STARTER_ROLES` 以改变发牌池

- **多语言支持**：当前交互为中文，可在 UI 层和 Prompt 层抽象文案

## 常见问题

- **Q：是否必须 6 人？**
  - A：当前实现校验恰好 6 名玩家。如需扩展，需修改 `GameEngine` 和相关配置。

- **Q：能否查看夜晚行动详情？**
  - A：运行时添加 `--reveal-log` 参数，结算后会展示夜间行动日志摘要。

- **Q：LLM 版支持哪些模型？**
  - A：理论上支持所有 OpenAI 兼容的 API。通过 `BASE_URL` 和 `MODEL_NAME` 环境变量配置。

- **Q：如何自定义 LLM 的行为？**
  - A：修改 `role_prompts.py` 中的角色 Prompt 模板，或调整 `llm_agents.py` 中的系统提示。

## 许可

此项目用于学习与交流，未附带明确开源许可证。如需用于商业或二次分发，请先与作者沟通或补充许可证说明。
