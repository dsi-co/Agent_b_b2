# 个人模块 README — B2：Skill 工具函数模块

> **姓名**：计林敏
> **学号**：20236093
> **模块**：B2 — Skill 工具函数模块
> **方向**：B方向 Agent 智能体

---

## 1. 模块概述

### 1.1 模块名称

`B2 — Skill 工具函数模块（Skill工具函数模块）`

### 1.2 模块说明

B2 模块是整个 Agent 系统中**唯一负责实际功能执行**的模块。在 Agent 的"感知-决策-执行"闭环中，B2 处于**执行层**，将 LLM 的决策转化为实际可执行的操作。

B2 的核心职责是：接收由 B3（Tool Layer）传入的工具参数，执行具体的 Python 函数，并将结果包装为统一的 `SkillResult` 结构化格式返回。

```text
B2 解决的问题：
1. LLM 无法直接读取本地文件系统 → file_reader、local_file_search 提供文件访问能力
2. LLM 无法保证数学计算精确 → calculator 使用 AST 安全求值
3. LLM 无法解析结构化数据 → table_analyzer 分析 CSV/TSV 表格
4. LLM 无法生成格式化文件 → format_converter 将文本转换为 Markdown/JSON 并写入文件

设计目标：
- 每个 Skill 保持单一职责，功能纯粹、可独立测试
- 相同输入 → 相同输出（确定性），不依赖随机性
- 安全第一：路径穿越防护、AST 安全求值、沙箱代码执行
- 标准化返回：统一使用 SkillResult 格式包装所有结果
```

### 1.3 完成情况概览

| 类型 | 完成情况 |
|---|---|
| 基础要求 | 5 个基础 Skill 全部实现并可独立运行（calculator、file_reader、local_file_search、table_analyzer、format_converter），支持正常/异常双路径测试 |
| 进阶要求 | 四大增强：①结构化错误分类（3大类9种错误码）；②风险等级管控（LOW/MEDIUM/HIGH + 超时 + 限流）；③复合 Skill Pipeline（`$变量`引用）；④新增3个增强 Skill（local_file_search_enhanced、code_executor、composite_skill） |
| 可独立运行的演示 | 基础版 `b2_run_skill.py` + 增强版 `b2_enhanced_run_skill.py` 均提供独立 CLI 入口，`--list` 查看所有 Skill |
| 与团队系统集成情况 | 通过 `tools.yaml` 配置驱动注册，被 B3 动态加载调用，支持 B1→B3→B2 完整链路 |

---

## 2. 环境、模型与数据依赖

### 2.1 运行环境

| 项目 | 要求 |
|---|---|
| Python 版本 | 3.10 |
| 必要依赖 | `PyYAML==6.0.3`、`torch==2.7.1+cu118`、`transformers==5.12.1`、`accelerate==1.14.0`、`sentencepiece==0.2.1`、`safetensors==0.8.0`、`tokenizers==0.22.2`、`huggingface_hub==1.20.1` 等（完整列表见 `requirements.txt`） |
| 是否需要模型 | B2 模块本身不需要模型（B2 只执行确定性工具函数）。 |
| 是否需要 GPU | B2 模块不需要 GPU。 |
| 是否需要外部数据集 | 不需要。B2 使用项目内置的 `data/` 目录下的测试数据 |
| 操作系统 | Linux (Ubuntu)  |

### 2.2 模型依赖

B2 模块不直接依赖任何模型。B2 是纯粹的 Python 函数执行层，所有 Skill 都是确定性的（相同输入→相同输出），不使用 LLM、不加载模型权重。

模型由 B4 模块负责加载和调用，B2 仅作为被 B3 调用的工具函数层。因此：

- B2 的独立运行和测试不需要 GPU、不需要模型
- B2 参与完整系统联调时，模型由 B4 提供，B2 无需感知

### 2.3 数据集或样例数据依赖

B2 使用项目内置的预制测试数据，所有文件位于 `data/` 目录下，无需额外下载。

| 数据或文件 | 来源 | 项目内相对路径 | 用途 |
|---|---|---|---|
| 测试输入（正常） | 项目 | `data/tool_inputs/tool_input_calculator.json` | calculator 正常输入测试 |
| 测试输入（正常） | 项目 | `data/tool_inputs/tool_input_file_reader.json` | file_reader 正常输入测试 |
| 测试输入（正常） | 项目 | `data/tool_inputs/tool_input_file_search.json` | local_file_search 正常输入测试 |
| 测试输入（正常） | 项目 | `data/tool_inputs/tool_input_table_analyzer.json` | table_analyzer 正常输入测试 |
| 测试输入（正常） | 项目 | `data/tool_inputs/tool_input_format_converter.json` | format_converter 正常输入测试 |
| 测试输入（异常） | 项目 | `data/tool_inputs/tool_input_*_error.json` | 各 Skill 异常/边界输入测试 |
| 被读取的文档 | 项目 | `data/docs/agent_intro.txt` | file_reader / local_file_search 的读取目标 |
| 被分析的表格 | 项目 | `data/tables/results.csv` | table_analyzer 的 CSV 分析目标 |
| 工具配置 | 项目 | `configs/tools.yaml` | B2 Skill 注册表，声明模块路径、函数名、参数和返回值 |

### 2.4 环境准备命令

```bash
# 创建 conda 环境
conda create -n agent python=3.10 -y
conda activate agent

# 安装依赖
cd agent
pip install -r requirements.txt
```
---

## 3. 文件结构与接口边界

### 3.1 文件结构

```text
agent/
├── code/
│   ├── b2_run_skill.py              ←  基础版入口：路由分发与统一执行（5个Skill）
│   ├── b2_enhanced_run_skill.py     ←  增强版入口：错误分类+风险管控+限流+Pipeline
│   └── common/
│       ├── schemas.py               ← SkillResult / AIMessage / ToolMessage 标准格式定义
│       ├── io_utils.py              ← JSON / YAML / JSONL 读写工具
│       ├── path_utils.py            ← 路径解析与安全工具
│       └── logging_utils.py         ← 日志工具
├── skills/                           ←  B2 核心：Skill 实现文件
│   ├── __init__.py                  ← resolve_data_path 路径安全守卫 + SKILL_MODULES 注册表
│   ├── calculator.py                ← 基础：安全算术计算器（AST求值，4层安全防护）
│   ├── file_reader.py               ← 基础：本地文件读取（txt/md，自动截断）
│   ├── local_file_search.py         ← 基础：本地文件搜索（关键词匹配+上下文片段）
│   ├── table_analyzer.py            ← 基础：CSV/TSV表格分析（行列统计+数值统计）
│   ├── format_converter.py          ← 基础：格式转换（text→markdown/json，生成文件）
│   ├── local_file_search_enhanced.py ← 进阶：增强搜索（正则+10种文件类型+多线程并发）
│   ├── code_executor.py             ← 进阶：沙箱代码执行（AST安全检查+import白名单+超时）
│   └── composite_skill.py           ← 进阶：Pipeline编排（多Skill串联，$变量引用）
├── configs/
│   └── tools.yaml                   ←  B2 Skill 注册表（B3 通过它发现并调用 B2）
├── data/
│   └── tool_inputs/                 ← B2 测试数据
└── outputs/
    └── B2_skills/                   ← B2 输出目录（*_result.json + skill_run_log.jsonl）
    └── B2_test/                     ← B2 进阶输出目录
```

### 3.2 接口边界

| 类型 | 来源 / 去向 | 数据格式 | 说明 |
|---|---|---|---|
| 输入（独立运行） | CLI 用户 `--input` 参数 | JSON 文件（参数字典） | 如 `{"expression": "23 * 17 + 9"}` |
| 输入（集成运行） | B3（Tool Layer）通过 `importlib` 动态调用 | Python dict（args） | B3 从 AIMessage.tool_calls 提取参数后传入 |
| 输出（独立运行） | `outputs/B2_skills/{skill}_result.json` | JSON 对象（SkillResult） | 覆盖写入 |
| 输出（独立运行） | `outputs/B2_skills/skill_run_log.jsonl` | JSONL（追加写入） | 运行日志 |
| 输出（集成运行） | 返回给 B3 → 包装为 ToolMessage → 传给 B1 | Python dict（SkillResult） | `make_skill_result()` 标准格式 |
| 配置 | `configs/tools.yaml` | YAML | B2 通过此文件向 B3 声明：模块路径、函数名、参数、返回值 |

---

## 4. 基础要求实现与演示

### 4.1 基础功能说明

基础版本实现了 5 个确定性工具函数（Skill），覆盖 Agent 最常用的本地操作能力：

| Skill | 功能 | 关键设计 |
|-------|------|---------|
| `calculator` | 安全算术表达式计算 | 使用 `ast.parse(mode="eval")` 代替 `eval()`，4层安全防护（长度限制→AST解析→指数限制→结果范围校验） |
| `file_reader` | 读取本地 txt/md 文件 | 通过 `resolve_data_path()` 防路径穿越，支持 `max_chars` 截断，返回截断标志 |
| `local_file_search` | 在本地目录搜索文件 | `casefold()` 大小写无关匹配，`_snippet()` 提取上下文片段（前后各60字符），按分数排序 |
| `table_analyzer` | 分析 CSV/TSV 表格 | `csv.DictReader` 解析，自动识别数值列并用 `statistics.fmean` 计算 min/max/mean |
| `format_converter` | 文本格式转换 | 支持 markdown/json 两种目标格式；JSON支持两种输入自适应（已有JSON或 key:value 行格式） |

每个 Skill 均满足：
- 正常输入 → 返回正确业务结果
- 异常输入 → 捕获异常，返回 `status: "error"` 而非程序崩溃
- 所有输出统一包装为 `SkillResult` 格式

### 4.2 基础功能实现路径

| 文件 / 函数 / 脚本 | 作用 |
|---|---|
| `code/b2_run_skill.py` — `run_skill()` | B2 统一调度器：路由分发 → 动态加载 → 签名注入 → 执行计时 → 异常捕获 → SkillResult 包装 |
| `code/b2_run_skill.py` — `main()` | CLI 入口：解析 `--skill`/`--input`/`--outdir`/`--data_root` 参数 |
| `skills/calculator.py` — `calculator()` | 安全算术求值（AST 递归遍历） |
| `skills/file_reader.py` — `file_reader()` | 文件读取 + 截断 |
| `skills/local_file_search.py` — `local_file_search()` | 关键词搜索 + 片段提取 |
| `skills/table_analyzer.py` — `table_analyzer()` | CSV/TSV 解析 + 数值统计 |
| `skills/format_converter.py` — `format_converter()` | 文本→Markdown/JSON 转换 + 文件生成 |
| `skills/__init__.py` — `resolve_data_path()` | 路径安全守卫（防路径穿越攻击） |
| `common/schemas.py` — `make_skill_result()` | 统一 SkillResult 包装函数 |

```text
CLI 输入 → argparse 解析参数 → read_json(输入文件)
  → run_skill(skill_name, input_data, data_root, outdir)
    → importlib.import_module(SKILL_MODULES[skill_name])
    → inspect.signature(function) 自动注入 data_root/output_dir
    → try: output = function(**kwargs)   # 执行 Skill
      catch Exception: 包装为 error SkillResult
    → perf_counter() 计时
    → make_skill_result() 统一包装
  → write_json(result, {skill}_result.json)
  → append_jsonl(log, skill_run_log.jsonl)
```

`run_skill()` 调度器代码展示：

```python
def run_skill(skill_name: str, input_data: dict, data_root: str | None = None, output_dir: str | None = None) -> dict:
    """统一执行入口：路由 → 加载 → 注入 → 执行 → 包装"""
    if skill_name not in SKILL_MODULES:
        raise ValueError(f"unknown skill: {skill_name}")
    if not isinstance(input_data, dict):
        raise ValueError("skill input must be a JSON object")
    module = importlib.import_module(SKILL_MODULES[skill_name])
    function = getattr(module, skill_name)
    kwargs = dict(input_data)
    signature = inspect.signature(function)
    if "data_root" in signature.parameters:
        kwargs["data_root"] = data_root or str(DEFAULT_DATA_ROOT)
    if "output_dir" in signature.parameters:
        kwargs["output_dir"] = output_dir
    start = perf_counter()
    try:
        output = function(**kwargs)
        status = "success"
        error = None
    except Exception as exc:
        output = None
        status = "error"
        error = {"type": type(exc).__name__, "message": str(exc)}
    latency_ms = round((perf_counter() - start) * 1000, 3)
    return make_skill_result(skill_name, status, input_data, output, error, latency_ms)
```

**关键设计决策**：
- **动态加载**：`importlib.import_module` 实现零耦合——新增 Skill 只需加一个模块文件和一行注册表
- **签名注入**：`inspect.signature` 让 B3 可以自动注入 `data_root` 和 `output_dir`，Skill 无需感知调用环境
- **异常捕获**：业务异常不抛到外层，而是包装为 `status: "error"` 的 SkillResult

### 4.3 基础功能输入格式与样例

| 字段 / 输入文件 | 类型 / 格式 | 是否必需 | 说明 |
|---|---|---|---|
| `--skill` | CLI 参数，字符串 | 是 | Skill 名称：calculator / file_reader / local_file_search / table_analyzer / format_converter |
| `--input` | CLI 参数，文件路径 | 是 | 指向 JSON 输入文件，顶层必须是 JSON 对象 |
| `--outdir` | CLI 参数，目录路径 | 是 | 输出目录 |
| `--data_root` | CLI 参数，目录路径 | 否 | 数据根目录，未提供时使用项目 `data/` |

样例输入：

| 样例文件 | 用途 |
|---|---|
| `data/tool_inputs/tool_input_calculator.json` | `{"expression": "23 * 17 + 9"}` — 验证正常算术计算 |
| `data/tool_inputs/tool_input_calculator_error.json` | `{"expression": "__import__('os')"}` — 验证防代码注入 |
| `data/tool_inputs/tool_input_file_reader.json` | `{"path": "docs/agent_intro.txt", "max_chars": 2000}` — 验证文件读取 |
| `data/tool_inputs/tool_input_file_reader_error.json` | `{"path": "docs/missing.txt", "max_chars": 2000}` — 验证文件不存在处理 |
| `data/tool_inputs/tool_input_file_search.json` | `{"query": "Agent 工具调用", "root_dir": "docs", "file_types": ["txt","md"], "top_k": 5}` — 验证文件搜索 |
| `data/tool_inputs/tool_input_file_search_error.json` | `{"query": "Agent", "root_dir": "missing", "top_k": 5}` — 验证目录不存在处理 |
| `data/tool_inputs/tool_input_table_analyzer.json` | `{"path": "tables/results.csv", "max_rows_preview": 5, "describe": true}` — 验证表格分析 |
| `data/tool_inputs/tool_input_table_analyzer_error.json` | 不支持的文件类型 — 验证类型校验 |
| `data/tool_inputs/tool_input_format_converter.json` | `{"text": "a: 1\nb: 2", "target_format": "markdown"}` — 验证格式转换 |
| `data/tool_inputs/tool_input_format_converter_error.json` | `{"text": "", "target_format": "json"}` — 验证空文本拒绝 |

### 4.4 基础功能演示命令

```bash
cd agent/code

# calculator — 正常计算
python b2_run_skill.py --skill calculator \
  --input ../data/tool_inputs/tool_input_calculator.json \
  --outdir ../outputs/B2_skills

# calculator — 异常注入（防代码注入）
python b2_run_skill.py --skill calculator \
  --input ../data/tool_inputs/tool_input_calculator_error.json \
  --outdir ../outputs/B2_skills

# file_reader — 正常读取
python b2_run_skill.py --skill file_reader \
  --input ../data/tool_inputs/tool_input_file_reader.json \
  --outdir ../outputs/B2_skills

# file_reader — 文件不存在
python b2_run_skill.py --skill file_reader \
  --input ../data/tool_inputs/tool_input_file_reader_error.json \
  --outdir ../outputs/B2_skills

# local_file_search — 正常搜索
python b2_run_skill.py --skill local_file_search \
  --input ../data/tool_inputs/tool_input_file_search.json \
  --outdir ../outputs/B2_skills

# table_analyzer — 表格分析
python b2_run_skill.py --skill table_analyzer \
  --input ../data/tool_inputs/tool_input_table_analyzer.json \
  --outdir ../outputs/B2_skills

# format_converter — 格式转换
python b2_run_skill.py --skill format_converter \
  --input ../data/tool_inputs/tool_input_format_converter.json \
  --outdir ../outputs/B2_skills
```


### 4.5 基础功能输出格式

| 输出文件 / 返回字段 | 格式 | 说明 |
|---|---|---|
| `outputs/B2_skills/calculator_result.json` | JSON 对象（SkillResult） | calculator 最近一次运行的输入、结果/错误、耗时 |
| `outputs/B2_skills/file_reader_result.json` | JSON 对象（SkillResult） | file_reader 结果；output 包含 content、num_chars、source、truncated |
| `outputs/B2_skills/local_file_search_result.json` | JSON 对象（SkillResult） | 搜索结果；每项包含 path、score、snippet |
| `outputs/B2_skills/table_analyzer_result.json` | JSON 对象（SkillResult） | 表格行列数、列名、预览和数值列统计 |
| `outputs/B2_skills/format_converter_result.json` | JSON 对象（SkillResult） | 转换后的 formatted_text 和 generated_file_path |
| `outputs/B2_skills/skill_run_log.jsonl` | JSONL（追加写入） | B2 运行历史；每行记录时间、Skill、状态、结果路径和耗时 |


### 4.6 基础功能结果截图

**项目目录结构：**

![项目目录结构](https://i.ibb.co/Mkf5Vmdt/5f7bfe92bc54.webp)

**calculator 运行结果：**

| 正常执行 | 异常测试 |
|:---:|:---:|
| ![calculator正常](https://i.ibb.co/N64CvtdR/cdf55ee9f0b5.webp) | ![calculator异常](https://i.ibb.co/JWPsNX2c/d9581fbb7d7d.webp) |

**file_reader 运行结果：**

| 正常执行 | 异常测试 |
|:---:|:---:|
| ![file_reader正常](https://i.ibb.co/tTs1cC40/8ea275827bd8.webp) | ![file_reader异常](https://i.ibb.co/HDKNBkqm/48181b1308ea.webp) |

**local_file_search 运行结果：**

| 正常执行 | 异常测试 |
|:---:|:---:|
| ![local_file_search正常](https://i.ibb.co/FLqhfBYt/ee9000dcc255.webp) | ![local_file_search异常](https://i.ibb.co/nMgtFhWg/009663e452fe.webp) |

**table_analyzer 运行结果：**

| 正常执行（含统计） | 异常测试 |
|:---:|:---:|
| ![table_analyzer正常](https://i.ibb.co/MDZ0sY3N/eea70f05a1ff.webp) | ![table_analyzer异常](https://i.ibb.co/qLx1yCjb/a69b88272624.webp) |

**format_converter 运行结果：**

| 正常执行 | 异常测试 |
|:---:|:---:|
| ![format_converter正常](https://i.ibb.co/6JXyLt9Z/f28b33e09484.webp) | ![format_converter异常](https://i.ibb.co/JwTNXtrW/36bc80e2f81d.webp) |

**运行日志：**

![skill_run_log](https://i.ibb.co/j952JZTf/9a731529d965.webp)

---

## 5. 进阶要求实现与演示

### 5.1 选择的进阶要求

| 进阶要求 | 是否完成 | 对应文件 / 函数 | 简要说明 |
|---|---|---|---|
| 增强已有 Skill 功能 | 是 | `skills/local_file_search_enhanced.py` | 正则搜索 + 10种文件类型 + 大小写开关 + 多线程并发 |
| 支持更多 Skill 类型（沙箱执行） | 是 | `skills/code_executor.py` | AST安全检查 + import白名单(12个安全模块) + 超时控制 |
| 支持复合 Skill（Pipeline） | 是 | `skills/composite_skill.py` + `b2_enhanced_run_skill.py` — `run_composite()` | 多Skill顺序执行，`$变量.字段` 引用上一步输出 |
| 更细粒度的错误分类 | 是 | `b2_enhanced_run_skill.py` — `SkillError` 类 + `ERR_CODES` | 3大类(INPUT/EXEC/SYS) 9种结构化错误码 |
| 高耗时/高风险 Skill 管控 | 是 | `b2_enhanced_run_skill.py` — `RISK_CONFIG` + `check_rate_limit()` | 三级风险(LOW/MEDIUM/HIGH) + 超时控制 + 滑动窗口限流 |

### 5.2 进阶功能 1：结构化错误分类系统

#### 功能说明

基础版的异常处理只有一个通用的 `{"type": "ValueError", "message": "..."}` 格式，B3 和 B1 无法区分错误类型，只能模糊记录。增强版设计了3大类、9种结构化错误码，使 B3 可以据错误码做差异化处理（如 `SYS-429` 触发退避重试，`INPUT-001` 反馈给 B4 修正参数），B1 的 `trace.json` 也获得更精确的错误溯源。

#### 实现路径

| 文件 / 函数 / 脚本 | 作用 |
|---|---|
| `b2_enhanced_run_skill.py` — `ERR_CODES` | 错误码字典：INPUT/EXEC/SYS 三大类共9种错误码 |
| `b2_enhanced_run_skill.py` — `SkillError(Exception)` | 自定义异常类，携带 code、code_key、message、details |
| `b2_enhanced_run_skill.py` — `run_skill_with_errors()` | 将常见异常（FileNotFoundError、PermissionError等）映射为对应错误码 |
| `b2_enhanced_run_skill.py` — `run_skill_safe()` | 安全执行包装，任何异常都转为标准化 dict，绝不崩溃 |

```text
Skill 执行异常 → FileNotFoundError → run_skill_with_errors() 
  → raise SkillError("FILE_NOT_FOUND", ...) 
  → run_skill_safe() 捕获 → make_skill_result("error", ..., error={"code": "INPUT-404", ...})
```

#### 输入格式与样例

| 字段 / 输入文件 / 配置项 | 类型 / 格式 | 是否必需 | 说明 |
|---|---|---|---|
| 异常类型 | Python Exception | 自动触发 | FileNotFoundError → INPUT-404, PermissionError → EXEC-403, TimeoutError → EXEC-001 |

#### 演示命令

```bash
cd agent/code


# 测试 SYS-404：未知 Skill
echo '{"expression": "1+1"}' > /tmp/t_unknown.json
python b2_enhanced_run_skill.py --skill does_not_exist --input /tmp/t_unknown.json --outdir ../outputs/B2_test

# 测试 INPUT-404：文件不存在
echo '{"path": "nonexistent/file.txt", "max_chars": 100}' > /tmp/t_notfound.json
python b2_enhanced_run_skill.py --skill file_reader --input /tmp/t_notfound.json --outdir ../outputs/B2_test
```

#### 输出格式

| 输出文件 / 返回字段 | 格式 | 说明 |
|---|---|---|
| `*_result.json` 中的 `error` 字段 | `{"code": "INPUT-404", "message": "...", "details": {...}}` | 结构化错误信息 |

#### 错误码速查表

| 错误码 | 含义 | 触发场景 |
|-------|------|---------|
| `INPUT-001` | 缺少必填参数 | 调用时没传必要参数 |
| `INPUT-002` | 参数类型错误 | 传了字符串应为数字 |
| `INPUT-003` | 参数值无效 | 传了不支持的选项 |
| `INPUT-404` | 文件不存在 | 读取的文件找不到 |
| `EXEC-001` | 执行超时 | 代码超过超时时间没跑完 |
| `EXEC-002` | 运行时错误 | 执行过程中出异常 |
| `EXEC-403` | 权限拒绝 | 尝试危险操作 |
| `EXEC-010` | 复合步骤失败 | Pipeline 某一步出错 |
| `SYS-404` | 未知 Skill | Skill 名字写错了 |
| `SYS-429` | 限流触发 | 调用太频繁被限制 |

#### 运行图片

![SYS-404错误](https://i.ibb.co/LXX7QFj4/fa421ab31c72.webp)
![INPUT-404错误](https://i.ibb.co/84dC7Ddx/4f812ed9e7cb.webp)
---

### 5.3 进阶功能 2：风险等级管控 + 限流器

#### 功能说明

对 8 个 Skill 划分 LOW/MEDIUM/HIGH 三个风险等级，每个等级配置不同的超时时间和限流策略。高风险 Skill（如 `code_executor`）执行时在 stderr 输出 `[!]` 警告，超时使用 `ThreadPoolExecutor` 实现真正的超时中断。限流器使用滑动窗口算法（60秒窗口），线程安全。

#### 实现路径

| 文件 / 函数 / 脚本 | 作用 |
|---|---|
| `b2_enhanced_run_skill.py` — `RiskLevel` | 风险等级常量定义 |
| `b2_enhanced_run_skill.py` — `RISK_CONFIG` | 每个 Skill 的 (风险等级, 超时秒数, 限流次/分钟) 配置 |
| `b2_enhanced_run_skill.py` — `check_rate_limit()` | 滑动窗口限流检查，线程安全（`threading.Lock`） |
| `b2_enhanced_run_skill.py` — `run_skill()` 中超时逻辑 | `ThreadPoolExecutor` + `future.result(timeout)` |

```text
调用 run_skill() → 查 RISK_CONFIG[skill] → (risk, timeout, rate)
  → check_rate_limit(skill, rate)  # 滑动窗口检查
  → risk == HIGH → print([!] 警告)
  → timeout < 60 → ThreadPoolExecutor 超时执行
  → timeout >= 60 → 直接同步执行
```

#### 风险等级配置

| Skill | 风险等级 | 超时 | 限流 | 原因 |
|-------|:------:|:----:|:----:|------|
| calculator | LOW | 60s | 无限制 | 纯计算，无副作用 |
| format_converter | LOW | 60s | 无限制 | 文本转换，安全 |
| file_reader | MEDIUM | 30s | 60/min | 涉及文件系统读取 |
| table_analyzer | MEDIUM | 30s | 60/min | 涉及文件读取+解析 |
| local_file_search | MEDIUM | 30s | 60/min | 遍历目录，可能耗时 |
| local_file_search_enhanced | MEDIUM | 60s | 30/min | 多线程+更多文件类型 |
| code_executor | **HIGH** | **10s** | **10/min** | 执行用户代码，高风险 |
| composite_skill | **HIGH** | **30s** | **10/min** | 串联多个 Skill，影响面大 |

#### 演示命令

```bash
cd agent/code

# 查看所有 Skill 及风险等级
python b2_enhanced_run_skill.py --list

# 测试高风险警告（code_executor 执行时 stderr 输出 [!]）
echo '{"code": "result = sum(range(100))", "timeout_s": 5}' > /tmp/t_c.json
python b2_enhanced_run_skill.py --skill code_executor --input /tmp/t_c.json --outdir ../outputs/B2_test
```

#### 运行图片

![skill_list](https://i.ibb.co/b4cW0Hr/8d1c9898fa43.webp)
![code_executor正常](https://i.ibb.co/h1RWkH4b/84c879862bb3.webp)

---

### 5.4 进阶功能 3：沙箱代码执行

#### 功能说明

新增 `code_executor` Skill，允许 Agent 执行用户提供的 Python 代码片段。采用**三层安全防护**：
1. **AST 安全检查**：解析代码 AST，禁止 `exec/eval/compile/open/__import__` 等危险函数调用
2. **Import 白名单**：只允许导入 12 个安全模块（math、json、re、random、collections、itertools、functools、statistics、decimal、datetime、typing、textwrap、string）
3. **超时控制**：1-30 秒可配置超时，使用线程 + `join(timeout)` 实现

#### 演示命令

```bash
cd agent/code

# 正常执行
echo '{"code": "result = sum(x*x for x in range(100))", "timeout_s": 5}' > /tmp/t_c.json
python b2_enhanced_run_skill.py --skill code_executor --input /tmp/t_c.json --outdir ../outputs/B2_test

# 安全防护：禁止 import os
echo '{"code": "import os\nresult = os.listdir(\".\")", "timeout_s": 5}' > /tmp/t_b.json
python b2_enhanced_run_skill.py --skill code_executor --input /tmp/t_b.json --outdir ../outputs/B2_test

# 安全防护：禁止 open()
echo '{"code": "f=open(\"/etc/passwd\")\nresult=f.read()", "timeout_s": 5}' > /tmp/t_open.json
python b2_enhanced_run_skill.py --skill code_executor --input /tmp/t_open.json --outdir ../outputs/B2_test

# 超时控制：死循环切断
echo '{"code": "while True: pass", "timeout_s": 3}' > /tmp/t_timeout.json
timeout 10 python b2_enhanced_run_skill.py --skill code_executor --input /tmp/t_timeout.json --outdir ../outputs/B2_test
```

#### 运行图片

| 正常执行 | 安全拦截 | 超时切断 |
|:---:|:---:|:---:|
| ![code正常](https://i.ibb.co/JwQNYjz4/67229527d02d.webp) | ![code拦截](https://i.ibb.co/4wn0ddBs/ccd2a247bd86.webp) | ![code超时](https://i.ibb.co/TBhPxrF5/918d3f4b4b18.webp) |

---

### 5.5 进阶功能 4：复合 Skill Pipeline

#### 功能说明

新增 `composite_skill`，支持将多个 Skill 串联为顺序执行管道。通过 `$变量名` 和 `$变量名.字段.子字段` 实现步骤间的数据引用。原本需要 B1→B3→B2 多次往返的复合任务，现在 B3 一次调用即可完成，减少了 Agent Loop 的决策轮次和 messages 长度。

**Pipeline 输入格式示例**：

```json
{
  "pipeline": [
    {
      "name": "读取文件",
      "skill": "file_reader",
      "input": {"path": "docs/agent_intro.txt", "max_chars": 300},
      "output_var": "c"
    },
    {
      "name": "转换为Markdown",
      "skill": "format_converter",
      "input": {"text": "$c.content", "target_format": "markdown"},
      "output_var": "r"
    }
  ]
}
```

**核心实现代码**（`b2_enhanced_run_skill.py` — `run_composite()` 函数）：

```python
def run_composite(pipeline: list[dict], data_root: str = None, outdir: str = None) -> dict:
    """顺序执行 pipeline，$var 引用上一步输出，支持点号路径（如 $c.content）"""
    context = {}
    steps = []
    ok = True
    for idx, step in enumerate(pipeline):
        name = step.get("name", f"step{idx+1}")
        skill = step.get("skill")
        inp = dict(step.get("input", {}))
        out_var = step.get("output_var", f"r{idx+1}")
        if not skill:
            steps.append({"name": name, "status": "error", "error": "缺少 skill 字段"})
            ok = False; break

        # ★ 变量替换：支持点号路径深层取值（如 $c.content）
        for k, v in inp.items():
            if isinstance(v, str) and v.startswith("$"):
                ref = v[1:]
                parts = ref.split(".")
                val = context
                try:
                    for p in parts:
                        if isinstance(val, dict):
                            val = val[p]
                        else:
                            raise KeyError(p)
                    inp[k] = val
                except (KeyError, TypeError):
                    steps.append({"name": name, "status": "error",
                                  "error": f"未找到变量 ${ref}"})
                    ok = False; break
        if not ok:
            break

        # 调用 run_skill_safe 执行当前 Skill
        result = run_skill_safe(skill, inp, data_root, outdir)
        if result["status"] == "success":
            context[out_var] = result["output"]
        steps.append({"name": name, "skill": skill, "status": result["status"],
                       "error": result.get("error")})
        if result["status"] != "success":
            ok = False
            break

    return {"pipeline_status": "success" if ok else "error", "steps": steps,
            "context_keys": list(context.keys())}
```

**设计要点**：
- **顺序执行**：前一步 `status="success"` 才执行下一步，`stop_on_failure` 控制失败行为
- **变量传递**：`$变量名.字段.子字段` 点号路径支持任意深度的 dict 嵌套访问
- **独立记录**：每步结果独立记录在 `steps[]` 中，失败时可精确定位到哪一步出问题
- **安全包装**：每步通过 `run_skill_safe()` 执行，确保单个步骤异常不会导致整个 Pipeline 崩溃



#### 演示命令

```bash
cd agent/code

# 文件读取 → 格式转换
echo '{"pipeline":[{"name":"读","skill":"file_reader","input":{"path":"docs/agent_intro.txt","max_chars":300},"output_var":"c"},{"name":"转","skill":"format_converter","input":{"text":"$c.content","target_format":"markdown"},"output_var":"r"}]}' > /tmp/t_p.json
python b2_enhanced_run_skill.py --skill composite_skill --input /tmp/t_p.json --outdir ../outputs/B2_test

# 计算器 → JSON格式转换
echo '{"pipeline":[{"name":"算","skill":"calculator","input":{"expression":"(1+2+3+4+5)*100"},"output_var":"n"},{"name":"转","skill":"format_converter","input":{"text":"$n.result","target_format":"json"},"output_var":"r"}]}' > /tmp/t_p2.json
python b2_enhanced_run_skill.py --skill composite_skill --input /tmp/t_p2.json --outdir ../outputs/B2_test
```

#### 运行图片

| 文件读取→Markdown转换（输出结果） | 计算器→JSON转换（输出结果） |
|:---:|:---:|
| ![pipeline_fileread_md](https://i.ibb.co/SD6GrMGH/2833e3557450.webp) | ![pipeline_calc_json](https://i.ibb.co/Y4syCd59/a6e194e3160e.webp) |

| 文件读取→格式转换 | 计算器→格式转换 |
|:---:|:---:|
| ![pipeline_fileread_terminal](https://i.ibb.co/JFG2TfXQ/229c4262c29c.webp) | ![pipeline_calc_terminal](https://i.ibb.co/5HB40FC/c343af66ea7a.webp) |

---

### 5.6 进阶功能 5：增强文件搜索

#### 功能说明

在基础版 `local_file_search` 之上增强：
- 支持 10 种文件类型（.txt/.md/.csv/.json/.py/.yaml/.yml/.html/.xml/.log）
- 支持正则表达式搜索
- 大小写开关（`case_sensitive` 参数）
- 多线程并发搜索（`ThreadPoolExecutor`，max_workers=4）
- 返回 `stats`（total/matched 文件数统计）

#### 演示命令

```bash
cd agent/code

echo '{"query": "Agent", "file_types": ["txt","md"], "top_k": 3}' > /tmp/t_s.json
python b2_enhanced_run_skill.py --skill local_file_search_enhanced --input /tmp/t_s.json --outdir ../outputs/B2_test
```

#### 运行图片

![enhanced_search](https://i.ibb.co/3mZf2qCh/6fad1a84271b.webp)

---

### 5.7 增强版运行日志

增强版所有 Skill 的运行记录统一写入 `skill_run.jsonl`，包含时间戳、Skill 名称、状态和输出路径。

![skill_run_log](https://i.ibb.co/0yfYvL8t/805af759c754.webp)

---

## 6. 与团队系统的集成说明

### 调用链路

B2 模块通过 **B3（Tool Layer）** 作为唯一调用者接入团队系统：

```
B1(Runtime) → B4(LLM决策) → B3(Tool Layer) → B2(Skill) → 返回 SkillResult → B3 → B1
```

### 集成方式

1. **配置驱动**：B2 的每个 Skill 在 `configs/tools.yaml` 中声明 `module`（Python模块路径）和 `function`（导出函数名）
2. **动态加载**：B3 通过 `importlib.import_module(module).function(**args)` 动态调用
3. **参数注入**：B3 通过 `inspect.signature` 自动注入 `data_root` 和 `output_dir`
4. **返回契约**：B2 返回标准 `SkillResult` → B3 包装为 `ToolMessage` → B1 追加到 `messages[]`

### 联调命令

```bash
# Step 1: B2 独立验证
python b2_run_skill.py --skill calculator --input ../data/tool_inputs/tool_input_calculator.json --outdir ../outputs/B2_skills

# Step 2: B3→B2 集成验证
python b3_tool_layer.py --tools_config ../configs/tools.yaml --toolset basic_tools --tool_calls ../data/messages/ai_message_with_tool_calls.json --execute --outdir ../outputs/B3_tools

# Step 3: B1→B3→B2 集成验证 (mock)
python b1_agent_runtime.py --input ../data/runtime_input.json --tools_config ../configs/tools.yaml --memory_config ../configs/memory.yaml --model_config ../configs/model.yaml --llm_mode mock --outdir ../outputs/B1_runtime

# Step 4: 全系统端到端验证
python run_full_demo.py --input ../data/runtime_input.json --tools_config ../configs/tools.yaml --memory_config ../configs/memory.yaml --model_config ../configs/model.yaml --llm_mode prompt_json --outdir ../outputs/full_demo
```

---

## 7. 已知问题与后续改进

| 问题 | 当前原因 | 后续改进 |
|---|---|---|
| Pipeline 不支持条件分支 | composite_skill 只实现了顺序执行 | 引入 `condition` 字段支持 if-else 分支 |
| 限流器只在单进程内有效 | 使用内存中的 `_call_log` 字典 | 改用 Redis 或文件锁实现跨进程限流 |
| code_executor 沙箱依赖 AST 分析 | `exec()` 本身是危险的，黑名单可能被绕过 | 使用 Docker 容器或 `restrictedpython` 实现真正隔离 |
| 缺少 Skill 执行结果的缓存 | 相同参数每次都重新执行 | 基于参数哈希的内存缓存，减少重复计算 |
| 错误码需要手动维护 | ERR_CODES 字典分散在代码中 | 抽取到独立配置文件，支持动态加载 |
