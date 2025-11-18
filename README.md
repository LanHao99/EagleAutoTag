# Eagle Auto Tagger

这是一个利用多模态大型语言模型（Multimodal Large Language Models）为 Eagle 素材库中的图片和字体文件自动生成标签（Tags）和注释（Annotation）的 Python 脚本。

## 主要功能

- **自动化处理**：自动为图片和字体文件生成描述性的标签和注释。
- **双模式支持**：支持两种模式运行：
  1.  **本地模式**：通过 [LM Studio](https://lmstudio.ai/) 等工具在本地部署和调用模型。
  2.  **云端模式**：通过 API 调用云服务提供商的模型（当前已集成通义千问 `qwen-vl-max`）。
- **高度可配置**：通过 `lm_config.json` 文件，可以轻松配置模型、API密钥、提示词模板和处理规则。
- **自定义提示词**：可以为不同文件类型（如 `.jpg`, `.png`, `.ttf`）指定不同的提示词模板。
- **跨平台**：基于 Python，可在 Windows, macOS, Linux 等系统上运行。

## 工作流程

1.  脚本被触发运行（例如，通过 `运行打标.bat`）。
2.  读取 `lm_config.json` 配置文件，获取当前要使用的模式（本地/云端）、模型参数等信息。
3.  根据文件类型（图片或字体），准备要发送给模型的数据。
4.  加载对应的提示词（Prompt）模板文件。
5.  将数据和提示词发送给指定的大语言模型（本地或云端）。
6.  接收模型返回的 JSON 格式结果，其中包含生成的标签和注释。
7.  （后续步骤）将这些信息更新到 Eagle 中的对应素材上。

## 文件结构

```
/
├── lm_clipboard_tag.py     # 主程序脚本
├── restore.py              #还原操作脚本    
├── lm_config.json          # 配置文件，所有设置都在这里
├── requirements.txt        # Python 依赖库
├── 运行打标.bat            # Windows 下的快捷运行脚本
├── 还原打标.bat            # Windows 下的快捷运行脚本
├── PIC通用反推标签.txt     # 图片文件的提示词模板
├── 字体反推提示模板.txt      # 字体文件的提示词模板
└── README.md               # 项目说明文档
```

## 安装与配置

### 1. 前置需求

1.  **安装 Python 依赖**:
    -   确保您已安装 Python 3.x。
    -   运行以下命令来安装所需的库：
        ```bash
        pip install -r requirements.txt
        ```

2.  **配置本地环境 (仅本地模式需要)**:
    -   **安装 LM Studio**: 从 [官网](https://lmstudio.ai/) 下载并安装 LM Studio。
    -   **配置硬件加速**: 在 LM Studio 的设置中，将硬件加速（Hardware Acceleration）设置为 `Vulkan` 以获得最佳性能。
    -   **下载模型**: 在 LM Studio 内搜索并下载推荐的模型，例如：
        -   `qwen/qwen3-vl-4b`
        -   `qwen/Qwen3-VL-30B-A3B-Instruct`
    -   **加载模型**: 将下载好的模型加载到本地AI服务器上。


### 2. 配置 `lm_config.json`

这是最关键的一步。打开 `lm_config.json` 文件进行修改。

#### 模式选择

-   `provider_mode`: 设置为 `1` 使用 **本地模式**，设置为 `2` 使用 **云端模式**。

#### 本地模式配置 (provider_mode = 1)

-   `local_base_url`: 设置你本地模型服务（如 LM Studio）的 API 地址，通常是 `http://localhost:1234/v1`。
-   `local_model`: 设置加载到本地服务中的模型标识符。

#### 云端模式配置 (provider_mode = 2)

-   `cloud_base_url`: 云服务商的 API 地址。默认已填好通义千问的地址。
-   `cloud_model`: 要使用的云端模型名称，例如 `qwen-vl-max`。
-   `api_key`: **（重要）** 填入你的云服务商提供的 API Key。

#### 其他配置

-   `templates_by_ext`: 为不同后缀名的文件指定不同的提示词模板文件。
-   `image_rules` / `font_rules`: 控制是否为图片/字体生成注释和标签。
-   模型参数（`temperature`, `top_p` 等）：根据需要调整模型的创造性和随机性。

## 如何使用

1.  完成上述安装与配置。
2.  **对于本地模式**：确保你的本地模型服务（如 LM Studio）已经启动，并加载了正确的模型。
3.  **对于云端模式**：确保你的 API Key 正确且账户有足够余额。
4.  在eagle复制文件的路径, 双击 `运行打标.bat` 或在终端中运行 `python lm_clipboard_tag.py` 来启动打标。
5.  在eagle复制文件的路径, 双击 `还原打标.bat` 或在终端中运行 `python lm_clipboard_tag.py` 来启动还原操作。