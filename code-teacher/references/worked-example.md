# 完整示例：用这套方法拆解一个 RAG Agent 项目

用一个真实项目（带 RAG 总结能力的 ReAct Agent + Streamlit 界面）演示整套方法。
这正是那节项目课的项目，方便你把"方法"和"你看过的课"对上号。

## 项目长什么样（地图）

```
agent/
  tools/
    agent_tools.py        # 给 agent 用的工具：天气、定位、用户信息、rag 总结…
    middleware.py         # 中间件：监控、日志、prompt 切换
  react_agent.py          # class ReactAgent，组装并运行 agent
config/                   # 配置文件
data/                     # 数据
model/
  factory.py              # chat_model / embed_model 工厂
prompts/                  # 提示词模板
rag/
  rag_service.py          # class RagSummarizeService
  vector_store.py         # class VectorStoreService
utils/
  config_handler.py / file_handler.py / logger_handler.py / path_tools.py / prompt_loader.py
app.py                    # Streamlit 网页入口
```

## 一张依赖图（地图的核心）

箭头表示"依赖 / 调用"：

```
app.py
  └── ReactAgent (react_agent.py)
        ├── middleware.py
        ├── agent_tools.py ──┐
        │                    └── RagSummarizeService (rag_service.py)
        │                             ├── VectorStoreService (vector_store.py)
        │                             │        ├── factory.embed_model
        │                             │        └── utils (file_handler, path_tools…)
        │                             ├── factory.chat_model
        │                             └── prompts / prompt_loader
        └── factory.chat_model (model/factory.py)

叶子节点（不 import 项目内其他模块）：utils/ 各模块、prompts
```

## 用方法读懂它：自底向上、从叶子到入口

### 第 0 步 看地图
读 README，知道它是"上传文档 → 问问题 → agent 用 RAG 总结文档并回答"。入口是 `app.py`。
追 import 关系画出上面这张依赖图，并产出一张 HTML 架构图（看得清各文件的函数、类的方法与属性、谁依赖谁）。

### 第 1 步 找叶子节点
图里不依赖项目内其他模块的文件：`utils/`（config_handler、path_tools、file_handler、logger_handler、prompt_loader）和 `prompts/`。这就是起点。

### 第 2 步 沿依赖反向、自底向上读（三层）
- **第一层 · 基础设施**：先读 `utils/`——`file_handler`（怎么读文档）、`path_tools`、`prompt_loader`（怎么加载提示词）。被上面所有人复用。
- **第二层 · 核心服务**：`factory.py`（怎么造 embed_model / chat_model）→ `VectorStoreService`（依赖 utils + factory，负责切分/检索）→ `RagSummarizeService`（依赖 vector_store + factory + prompts，负责检索后总结）→ `agent_tools.py`（把 rag_service 等包装成工具）。每一步用到的东西，上一步都已读过。
- **第三层 · 组装**：`middleware.py` + `ReactAgent`（用工具 + 模型工厂组装出会调用工具的 agent）。

### 第 3 步 最后读入口 / 胶水
`app.py`：把 ReactAgent 接到 Streamlit 界面、处理用户输入与流式输出。它依赖前面一切，所以放最后。

### 读完自测
试着回答："要把检索从'相似度 Top-K'换成'带重排序'，得动哪些文件？"
大概是：`vector_store.py`（检索逻辑）→ 可能在 `factory.py` 加个 rerank 模型 → `rag_service.py` 的 `retrieve_docs` 接上。
能顺畅答出来，就说明真的读懂了。

## 课程顺序为什么这样（= 依赖图的拓扑排序）

| 顺序 | 写了什么 | 层 | 为什么这时候写 |
|---|---|---|---|
| 0 | 架构图 | 看地图 | 先建立全局认知 |
| 1 | `utils/` | 第一层 | 叶子，谁都不依赖 |
| 2 | `vector_store.py` + `factory.py` | 第二层 | 依赖 utils |
| 3 | `rag_service.py` | 第二层 | 依赖向量库 + 工厂 + 提示词 |
| 4 | `agent_tools.py` | 第二层 | 把 rag_service 等包装成工具 |
| 5 | `middleware.py` + `react_agent.py` | 第三层 | 用工具 + 模型组装 agent |
| 6 | `app.py` | 第三层 | 依赖以上全部，最后接界面 |

每一步要用到的东西，上一步都已写好且能跑——这就是"自底向上、按依赖顺序"的好处：**没有占位，每步可测，读 / 写都不会撞见没见过的模块。**

## 一句话收尾

**看任何陌生项目：先看地图（画依赖图）→ 找叶子 → 沿依赖反向自底向上逐个读 → 最后读入口/胶水 → 用"加个功能要改哪"自测。**
