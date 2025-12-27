import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import base64

def get_models(base_url: str, timeout: float):
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer lm-studio"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
        return [m.get("id") for m in data.get("data", [])]

def chat(prompt: str, model: str, base_url: str, temperature: float, max_tokens: int, system: str, timeout: float, image_b64: str = "", extras: dict | None = None):
    url = base_url.rstrip("/") + "/chat/completions"
    if image_b64:
        user_content = [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image_b64}}]
    else:
        user_content = prompt
    payload = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user_content}],
        "temperature": temperature,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if extras:
        payload.update(extras)
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer lm-studio"}
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        print(content)

def chat_stream(prompt: str, model: str, base_url: str, temperature: float, max_tokens: int, system: str, timeout: float, image_b64: str = "", extras: dict | None = None):
    url = base_url.rstrip("/") + "/chat/completions"
    if image_b64:
        user_content = [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image_b64}}]
    else:
        user_content = prompt
    payload = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user_content}],
        "temperature": temperature,
        "stream": True,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if extras:
        payload.update(extras)
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer lm-studio"}
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            try:
                line = raw.decode("utf-8", errors="ignore").strip()
            except Exception:
                line = ""
            if not line:
                continue
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            choices = obj.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                print(content, end="", flush=True)
    print()

def completions(prompt: str, model: str, base_url: str, temperature: float, max_tokens: int, timeout: float, extras: dict | None = None):
    url = base_url.rstrip("/") + "/completions"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if extras:
        payload.update(extras)
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer lm-studio"}
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
        choice = data.get("choices", [{}])[0]
        text = choice.get("text", "")
        print(text)

def completions_stream(prompt: str, model: str, base_url: str, temperature: float, max_tokens: int, timeout: float, extras: dict | None = None):
    url = base_url.rstrip("/") + "/completions"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "stream": True,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if extras:
        payload.update(extras)
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer lm-studio"}
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            try:
                line = raw.decode("utf-8", errors="ignore").strip()
            except Exception:
                line = ""
            if not line:
                continue
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            choices = obj.get("choices", [])
            if not choices:
                continue
            text = choices[0].get("text", "")
            if text:
                print(text, end="", flush=True)
    print()

def read_text_file(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="gbk", errors="ignore") as f:
            return f.read()

def read_image_b64(path: str):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def read_json_file(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(path, "r", encoding="gbk", errors="ignore") as f:
            return json.load(f)

def resolve_model(model_arg: str, base_url: str, timeout: float):
    if model_arg:
        return model_arg
    env_model = os.getenv("LMSTUDIO_MODEL")
    if env_model:
        return env_model
    try:
        models = get_models(base_url, timeout)
        if models:
            return models[0]
    except Exception:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(prog="lm-studio-client", description="调用本地 LM Studio 输出")
    parser.add_argument("--prompt", required=True, help="输入提示")
    parser.add_argument("--model", help="模型名称，留空则自动选择或读取环境变量 LMSTUDIO_MODEL")
    parser.add_argument("--base-url", default="http://localhost:1234/v1", help="服务地址，默认 http://localhost:1234/v1")
    parser.add_argument("--temperature", type=float, default=0.7, help="温度")
    parser.add_argument("--top-p", type=float, default=1.0, help="Top P")
    parser.add_argument("--frequency-penalty", type=float, default=0.0, help="频率惩罚")
    parser.add_argument("--presence-penalty", type=float, default=0.0, help="出现惩罚")
    parser.add_argument("--stop", nargs='*', default=[], help="停止词，空格分隔多个")
    parser.add_argument("--max-tokens", type=int, default=0, help="最大生成 token 数")
    parser.add_argument("--system", default="", help="系统提示")
    parser.add_argument("--template-file", default="", help="模板文件路径，作为系统提示或拼接到 prompt")
    parser.add_argument("--image-file", default="", help="图片文件路径，chat 模式中作为视觉输入")
    parser.add_argument("--mode", choices=["chat", "text"], default="chat", help="调用模式：chat 使用 /v1/chat/completions，text 使用 /v1/completions")
    parser.add_argument("--stream", action="store_true", help="流式输出")
    parser.add_argument("--config-file", default="lm_config.json", help="配置文件路径，JSON 格式")
    parser.add_argument("--timeout", type=float, default=60.0, help="请求超时时间秒")
    args = parser.parse_args()
    try:
        cfg = {}
        if args.config_file and os.path.isfile(args.config_file):
            cfg = read_json_file(args.config_file) or {}
        def get_val(name, default):
            val = getattr(args, name)
            parser_default = parser.get_default(name)
            if val == parser_default and name in cfg:
                return cfg.get(name, default)
            return val
        args.model = get_val("model", None) or args.model
        args.base_url = get_val("base_url", args.base_url)
        args.temperature = float(get_val("temperature", args.temperature))
        args.top_p = float(get_val("top_p", args.top_p))
        args.frequency_penalty = float(get_val("frequency_penalty", args.frequency_penalty))
        args.presence_penalty = float(get_val("presence_penalty", args.presence_penalty))
        args.max_tokens = int(get_val("max_tokens", args.max_tokens))
        args.system = get_val("system", args.system)
        if not args.template_file:
            args.template_file = cfg.get("template_file", args.template_file)
        model = resolve_model(args.model, args.base_url, args.timeout)
        if not model:
            print("未能确定模型，请通过 --model 或设置环境变量 LMSTUDIO_MODEL，并确保 LM Studio 已加载模型。", file=sys.stderr)
            sys.exit(2)
        system_prompt = args.system
        if args.template_file:
            tpl = read_text_file(args.template_file)
            
            # 尝试读取历史标签并插入到模板中
            history_tags_path = "history_tags.json"
            if os.path.exists(history_tags_path):
                try:
                    history_tags = read_json_file(history_tags_path)
                    if history_tags:
                        # 找到模板中需要插入标签库的位置
                        tag_lib_marker = "请优先使用标签库中存在的中文标签，确保生成的标签能够在标签库中找到："
                        if tag_lib_marker in tpl:
                            # 在标签库标记后插入历史标签
                            tpl_parts = tpl.split(tag_lib_marker)
                            if len(tpl_parts) == 2:
                                # 构建标签库内容
                                tags_content = "\n\n" + ",\n".join(history_tags[:1000]) + "\n\n"
                                # 重新组合模板
                                tpl = tpl_parts[0] + tag_lib_marker + tags_content + tpl_parts[1]
                except Exception as e:
                    print(f"读取历史标签失败：{e}", file=sys.stderr)
            
            if args.mode == "chat":
                system_prompt = tpl + ("\n\n" + system_prompt if system_prompt else "")
            else:
                args.prompt = tpl + "\n\n" + args.prompt
        image_b64 = ""
        if args.image_file and args.mode == "chat":
            image_b64 = read_image_b64(args.image_file)
        extras = {}
        if args.top_p is not None:
            extras["top_p"] = args.top_p
        if args.frequency_penalty:
            extras["frequency_penalty"] = args.frequency_penalty
        if args.presence_penalty:
            extras["presence_penalty"] = args.presence_penalty
        if args.stop:
            extras["stop"] = args.stop
        if args.mode == "chat":
            if args.stream:
                chat_stream(args.prompt, model, args.base_url, args.temperature, args.max_tokens, system_prompt, args.timeout, image_b64, extras)
            else:
                chat(args.prompt, model, args.base_url, args.temperature, args.max_tokens, system_prompt, args.timeout, image_b64, extras)
        else:
            if args.stream:
                completions_stream(args.prompt, model, args.base_url, args.temperature, args.max_tokens, args.timeout, extras)
            else:
                completions(args.prompt, model, args.base_url, args.temperature, args.max_tokens, args.timeout, extras)
    except urllib.error.URLError as e:
        print(f"连接失败：{e}", file=sys.stderr)
        sys.exit(2)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        print(f"HTTP 错误 {e.code}: {body}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
