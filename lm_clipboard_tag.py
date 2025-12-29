import os
import sys
import json
import base64
import argparse
import urllib.request
import urllib.error
import mimetypes
import subprocess
import csv
import io
from PIL import Image
import time
import shutil
import re

# 全局标签翻译字典
translations = {}

# 全局历史标签集合
history_tags = set()

# 历史标签文件路径
HISTORY_TAGS_FILE = "history_tags.json"

def load_translations():
    """加载Tags-zh.csv中的标签翻译字典"""
    global translations
    try:
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "Tags-zh.csv")
        
        with open(csv_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                if "," not in line:
                    print(f"警告: CSV第{line_num}行格式错误，缺少逗号")
                    continue
                en, zh = map(str.strip, line.split(",", 1))
                if not en or not zh:
                    print(f"警告: CSV第{line_num}行存在空字段")
                    continue
                translations[en] = zh
    except Exception as e:
        print(f"加载翻译文件失败: {e}")
        translations = {}

def load_history_tags():
    """加载历史标签记录"""
    global history_tags
    try:
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        history_file = os.path.join(script_dir, HISTORY_TAGS_FILE)
        
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history_tags = set(json.load(f))
    except Exception as e:
        print(f"加载历史标签失败: {e}")
        history_tags = set()

def save_history_tags():
    """保存历史标签记录"""
    try:
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        history_file = os.path.join(script_dir, HISTORY_TAGS_FILE)
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(list(history_tags), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史标签失败: {e}")

def update_history_tags(new_tags):
    """更新历史标签记录"""
    global history_tags
    if not isinstance(new_tags, list):
        return
    
    # 清理和筛选有效的标签
    valid_tags = []
    for tag in new_tags:
        if isinstance(tag, str):
            cleaned_tag = clean_tag(tag)
            if cleaned_tag and not is_bad_tag(cleaned_tag):
                valid_tags.append(cleaned_tag)
    
    # 如果有有效的标签，更新历史记录
    if valid_tags:
        import random
        
        # 添加新的标签
        history_tags.update(valid_tags)
        
        # 如果历史标签数量超过5000，随机删除多余的标签
        MAX_TAGS = 5000
        if len(history_tags) > MAX_TAGS:
            excess = len(history_tags) - MAX_TAGS
            # 随机删除多余的标签
            tags_to_remove = random.sample(list(history_tags), excess)
            for tag in tags_to_remove:
                history_tags.remove(tag)
        
        # 保存更新后的历史记录
        save_history_tags()

# 初始化标签翻译字典和历史标签
load_translations()
load_history_tags()

def read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        with open(path, "r", encoding="gbk", errors="ignore") as f:
            return json.load(f)
    except Exception:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="gbk", errors="ignore") as f:
                text = f.read()
    return parse_json_obj(text)

def write_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)

def read_text(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="gbk", errors="ignore") as f:
            return f.read()

def image_to_data_url(path: str):
    ext = os.path.splitext(path)[1].lower()
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        if ext in [".jpg", ".jpeg"]:
            mime = "image/jpeg"
        elif ext == ".png":
            mime = "image/png"
        elif ext == ".webp":
            mime = "image/webp"
        elif ext == ".gif":
            mime = "image/gif"
        elif ext in [".tif", ".tiff"]:
            mime = "image/tiff"
        elif ext == ".bmp":
            mime = "image/bmp"
        elif ext == ".avif":
            mime = "image/avif"
        elif ext == ".heic":
            mime = "image/heic"
        elif ext == ".ico":
            mime = "image/x-icon"
        else:
            mime = "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def data_url_to_base64(data_url: str):
    s = (data_url or "").strip()
    i = s.find("base64,")
    if i != -1:
        return s[i+7:]
    return s

def extract_message_text(msg: dict):
    if not isinstance(msg, dict):
        return ""
    cont = msg.get("content")
    if isinstance(cont, str):
        return cont
    if isinstance(cont, list):
        pieces = []
        for it in cont:
            if isinstance(it, dict):
                t = it.get("text") or it.get("content") or ""
                if isinstance(t, str) and t.strip():
                    pieces.append(t.strip())
        if pieces:
            return "\n".join(pieces)
    ot = msg.get("output_text")
    if isinstance(ot, str):
        return ot
    return ""

def fetch_image_data_url(url: str, timeout: float):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type") or ""
            if not (isinstance(ctype, str) and ctype.startswith("image/")):
                mime, _ = mimetypes.guess_type(url)
                if isinstance(mime, str) and mime.startswith("image/"):
                    ctype = mime
                else:
                    ctype = "image/png"
            b64 = base64.b64encode(raw).decode("ascii")
            return f"data:{ctype};base64,{b64}"
    except Exception:
        return ""

def call_lmstudio_text(base_url: str, model: str, system: str, prompt: str, temperature: float, extras: dict, timeout: float, auth_token: str):
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    if extras:
        payload.update(extras)
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token or 'lm-studio'}"}
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message")
        content = ""
        if isinstance(msg, dict):
            content = extract_message_text(msg)
        if not content:
            cont2 = choice.get("content")
            if isinstance(cont2, str):
                content = cont2
            elif isinstance(cont2, list):
                pieces = []
                for it in cont2:
                    if isinstance(it, dict):
                        t = it.get("text") or it.get("content") or ""
                        if isinstance(t, str) and t.strip():
                            pieces.append(t.strip())
                content = "\n".join(pieces)
        if not content:
            ot = choice.get("output_text") or data.get("output_text")
            if isinstance(ot, str):
                content = ot
        u = data.get("usage")
        return content, normalize_usage(u)

def parse_json_obj(text: str):
    t = (text or "").strip()
    if not t:
        return {}
    try:
        return json.loads(t)
    except Exception:
        try:
            i = t.find("{")
            j = t.rfind("}")
            if i != -1 and j != -1 and j > i:
                return json.loads(t[i:j+1])
        except Exception:
            pass
    return {}

def parse_font_output(text: str):
    obj = parse_json_obj(text)
    annotation_parts = []
    b = obj.get("base_info")
    c = obj.get("copyright")
    if isinstance(b, str) and b.strip():
        annotation_parts.append(b.strip())
    if isinstance(c, str) and c.strip():
        annotation_parts.append(c.strip())
    annotation = "\n".join(annotation_parts) if annotation_parts else ""
    def sanitize_urls(val):
        items = []
        def add_one(s):
            s = re.sub(r"[\[\]\(\)]", "", s.strip())
            if not s:
                return
            urls = re.findall(r"https?://[^\s]+", s)
            if urls:
                for u in urls:
                    u = u.rstrip(")].,;")
                    if u not in items:
                        items.append(u)
            else:
                if s not in items:
                    items.append(s)
        if isinstance(val, str):
            add_one(val)
        elif isinstance(val, list):
            for x in val:
                if isinstance(x, str):
                    add_one(x)
        return "\n".join(items)
    url_all = sanitize_urls(obj.get("license_url"))
    url = url_all.splitlines()[0].strip() if isinstance(url_all, str) and url_all.strip() else ""
    ban = {"family", "subfamily", "full_name", "fullname", "base_info", "copyright", "license_url"}
    tags = []
    for k, v in obj.items():
        if k in ban:
            continue
        if k == "weight":
            if isinstance(v, list):
                for x in v:
                    s = str(x).strip()
                    if s:
                        tags.append(f"weight:{s}")
            else:
                s = str(v).strip()
                if s:
                    tags.append(f"weight:{s}")
            continue
        if isinstance(v, list):
            for x in v:
                if isinstance(x, (str, int, float)):
                    s = str(x).strip()
                    if s:
                        tags.append(s)
        elif isinstance(v, (str, int, float)):
            s = str(v).strip()
            if s:
                tags.append(s)
    return annotation, url, tags

def update_font_metadata(font_path: str, out_text: str, rules: dict):
    d = os.path.dirname(font_path)
    meta_path = os.path.join(d, "metadata.json")
    before_obj = read_json(meta_path) or {}
    annotation, url, new_tags_raw = parse_font_output(out_text)
    existing = before_obj.get("tags") if isinstance(before_obj.get("tags"), list) else []
    existing_clean = dedup_tags(existing)
    incoming_clean = dedup_tags(new_tags_raw)
    merged = []
    seen = set()
    for x in existing_clean + incoming_clean:
        if x not in seen:
            seen.add(x)
            merged.append(x)
    mode_ann = get_rule(rules or {}, "annotation", 1)
    if annotation:
        if mode_ann == 2:
            before_obj["annotation"] = annotation
        else:
            prev = before_obj.get("annotation")
            if isinstance(prev, str) and prev.strip():
                if annotation not in prev:
                    before_obj["annotation"] = prev.strip() + "\n" + annotation
            else:
                before_obj["annotation"] = annotation
    if isinstance(url, str) and url.strip():
        before_obj["url"] = url
    mode_tags = get_rule(rules or {}, "tags", 2)
    if mode_tags == 2:
        before_obj["tags"] = incoming_clean
    else:
        before_obj["tags"] = merged
    write_json(meta_path, before_obj)
    final_tags = before_obj.get("tags") if isinstance(before_obj.get("tags"), list) else []
    
    # 更新历史标签记录
    update_history_tags(final_tags)
    
    return meta_path, existing_clean, final_tags

def get_clipboard_text():
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        t = r.clipboard_get()
        r.destroy()
        return t
    except Exception:
        try:
            out = subprocess.check_output(["powershell", "-NoProfile", "Get-Clipboard"], text=True)
            return out
        except Exception:
            return ""

def call_lmstudio(base_url: str, model: str, system: str, prompt: str, image_path: str, temperature: float, extras: dict, timeout: float):
    url = base_url.rstrip("/") + "/chat/completions"
    content = [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}}]
    payload = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}],
        "temperature": temperature,
    }
    if extras:
        payload.update(extras)
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer lm-studio"}
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        return msg.get("content", "")

def call_lmstudio_data(base_url: str, model: str, system: str, prompt: str, data_url: str, temperature: float, extras: dict, timeout: float, auth_token: str, provider: str, cloud_image_mode: str):
    url = base_url.rstrip("/") + "/chat/completions"
    prov = (provider or "").strip().lower()
    variants = []
    mode = (cloud_image_mode or "").strip().lower()
    if prov == "dashscope":
        if mode == "base64":
            # Standard OpenAI-compatible format for DashScope
            variants.append([
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ])
        else:
            # Standard OpenAI-compatible format for DashScope
            variants.append([
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ])
            variants.append([
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": data_url}
            ])
    else:
        variants.append([
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}}
        ])
    last_usage = None
    for content in variants:
        payload = {
            "model": model,
            "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}],
            "temperature": temperature,
        }
        if extras:
            payload.update(extras)
        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token or 'lm-studio'}"}
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.load(resp)
        except Exception as e:
            print(f"API call failed: {e}")
            continue
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message")
        text_out = ""
        if isinstance(msg, dict):
            text_out = extract_message_text(msg)
        if not text_out:
            cont2 = choice.get("content")
            if isinstance(cont2, str):
                text_out = cont2
            elif isinstance(cont2, list):
                pieces = []
                for it in cont2:
                    if isinstance(it, dict):
                        t = it.get("text") or it.get("content") or ""
                        if isinstance(t, str) and t.strip():
                            pieces.append(t.strip())
                text_out = "\n".join(pieces)
        if not text_out:
            ot = choice.get("output_text") or data.get("output_text")
            if isinstance(ot, str):
                text_out = ot
        u = data.get("usage")
        last_usage = normalize_usage(u)
        if isinstance(text_out, str) and text_out.strip():
            return text_out, last_usage
    return "", last_usage

def check_service(base_url: str, timeout: float, auth_token: str):
    try:
        url = base_url.rstrip("/") + "/models"
        headers = {"Authorization": f"Bearer {auth_token or 'lm-studio'}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            json.load(resp)
        return True
    except Exception:
        return False

def check_service_with_retry(base_url: str, timeout: float, retries: int, delay: float, auth_token: str):
    for i in range(int(retries)):
        if check_service(base_url, timeout, auth_token):
            return True
        if i < int(retries) - 1:
            time.sleep(float(delay))
    return False

def clean_tag(s: str):
    s = s.strip().strip('"').strip("'")
    s = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", s)
    # 删除异常符号：+，！，/，\，@，#，* 等
    s = re.sub(r"[+!\/\\@#*]", "", s)
    s = s.replace("\r", " ").replace("\n", " ")
    s = " ".join(s.split())
    return s

def is_bad_tag(s: str):
    t = (s or "").strip().lower()
    return t in {"{", "}", "tags"}

def get_auth_token(cfg: dict):
    token = None
    explicit = (cfg or {}).get("api_key") or ""
    if explicit.strip():
        token = explicit.strip()
    else:
        for name in ["DASHSCOPE_API_KEY", "LM_API_KEY", "OPENAI_API_KEY"]:
            v = os.environ.get(name)
            if v and v.strip():
                token = v.strip()
                break
    provider = ((cfg or {}).get("provider") or "").strip().lower()
    base = ((cfg or {}).get("base_url") or "").strip().lower()
    if not token:
        if "dashscope.aliyuncs.com" in base or provider == "dashscope":
            token = ""
        else:
            token = "lm-studio"
    return token

def normalize_usage(u):
    if not isinstance(u, dict):
        return None
    res = {}
    for k in ["prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens"]:
        v = u.get(k)
        if isinstance(v, (int, float)):
            res[k] = int(v)
    if "total_tokens" not in res:
        a = res.get("prompt_tokens")
        b = res.get("completion_tokens")
        c = res.get("input_tokens")
        d = res.get("output_tokens")
        if isinstance(a, int) and isinstance(b, int):
            res["total_tokens"] = a + b
        elif isinstance(c, int) and isinstance(d, int):
            res["total_tokens"] = c + d
    return res if res else None

def format_usage(u):
    if not isinstance(u, dict):
        return ""
    a = u.get("prompt_tokens")
    b = u.get("completion_tokens")
    t = u.get("total_tokens")
    c = u.get("input_tokens")
    d = u.get("output_tokens")
    if isinstance(a, int) and isinstance(b, int):
        return f"tokens: prompt {a}, completion {b}, total {t or a + b}"
    if isinstance(c, int) and isinstance(d, int):
        return f"tokens: input {c}, output {d}, total {t or c + d}"
    if isinstance(t, int):
        return f"tokens: total {t}"
    return ""

def get_rule(rules: dict, name: str, default_val: int):
    try:
        v = rules.get(name)
        if v is None:
            return int(default_val)
        return int(v)
    except Exception:
        return int(default_val)

def dedup_tags(items):
    result = []
    seen = set()
    for x in items or []:
        if not isinstance(x, str):
            x = str(x)
        s = clean_tag(x)
        if not s or is_bad_tag(s):
            continue
        # 翻译标签，如果在翻译字典中存在
        translated_tag = translations.get(s, s)
        if translated_tag not in seen:
            seen.add(translated_tag)
            result.append(translated_tag)
    return result

def parse_output_to_tags(text: str):
    t = (text or "").strip()
    if not t:
        return []
    try:
        reader = csv.reader(io.StringIO(t))
        row = next(reader)
        items = [clean_tag(x) for x in row if clean_tag(x)]
        if items:
            return items
    except Exception:
        pass
    if "," in t:
        items = [clean_tag(x) for x in t.split(",") if clean_tag(x)]
        if items:
            return items
    return [clean_tag(t)]

def update_tags_json(image_path: str, new_text: str, rules: dict):
    d = os.path.dirname(image_path)
    p = os.path.join(d, "metadata.json")
    obj = read_json(p) or {}
    existing = obj.get("tags")
    if not isinstance(existing, list):
        existing = []
    existing_clean = dedup_tags(existing)
    parsed = parse_json_obj(new_text)
    extra_tags = []
    if isinstance(parsed.get("tags"), list):
        for x in parsed.get("tags"):
            if isinstance(x, (str, int, float)):
                s = str(x).strip()
                if s:
                    extra_tags.append(s)
    if not extra_tags:
        try:
            lines = re.findall(r'"tags"\s*:\s*(.+)', new_text)
            for ln in lines:
                vals = re.findall(r'"([^\"]+)"', ln)
                for s in vals:
                    s2 = s.strip()
                    if s2:
                        extra_tags.append(s2)
        except Exception:
            pass
    incoming = extra_tags if extra_tags else parse_output_to_tags(new_text)
    incoming = dedup_tags(incoming)
    merged = []
    seen = set()
    for x in existing_clean + incoming:
        k = x
        if k not in seen:
            seen.add(k)
            merged.append(x)
    ann_val = ""
    if isinstance(parsed.get("annotation"), str) and parsed.get("annotation").strip():
        ann_val = parsed.get("annotation").strip()
    else:
        try:
            m = re.search(r'"annotation"\s*:\s*"([\s\S]*?)"', new_text)
            if m:
                ann_val = m.group(1).strip()
        except Exception:
            pass
    if ann_val:
        mode_ann = get_rule(rules or {}, "annotation", 1)
        if mode_ann == 2:
            obj["annotation"] = ann_val
        else:
            prev = obj.get("annotation")
            if isinstance(prev, str) and prev.strip():
                if ann_val not in prev:
                    obj["annotation"] = prev.strip() + "\n" + ann_val
            else:
                obj["annotation"] = ann_val
    mode_tags = get_rule(rules or {}, "tags", 1)
    if mode_tags == 2:
        obj["tags"] = incoming
    else:
        obj["tags"] = merged
    write_json(p, obj)
    final_tags = obj.get("tags") if isinstance(obj.get("tags"), list) else []
    
    # 更新历史标签记录
    update_history_tags(final_tags)
    
    return p, existing_clean, final_tags

def extract_tags_from_text(text: str):
    parsed = parse_json_obj(text)
    res = []
    if isinstance(parsed.get("tags"), list):
        for x in parsed.get("tags"):
            s = str(x).strip()
            if s:
                res.append(s)
        return res
    try:
        lines = re.findall(r'"tags"\s*:\s*(.+)', text)
        for ln in lines:
            vals = re.findall(r'"([^\"]+)"', ln)
            for s in vals:
                s2 = s.strip()
                if s2:
                    res.append(s2)
        if res:
            return res
    except Exception:
        pass
    return parse_output_to_tags(text)

def parse_paths(text: str):
    items = []
    for line in text.splitlines():
        s = line.strip().strip('"').strip("'")
        if not s:
            continue
        if s.startswith("http://") or s.startswith("https://"):
            items.append(s)
            continue
        ext = os.path.splitext(s)[1].lower()
        if os.path.isfile(s):
            # 支持所有存在的文件格式
            items.append(s)
        else:
            if ext in [
                ".ttf", ".otf", ".ttc", ".woff", ".woff2"
            ]:
                items.append(s)
    return items

def find_thumbnail(file_path: str):
    """在给定文件的路径下查找名称包含thumbnail的图片"""
    # 获取文件所在目录
    dir_path = os.path.dirname(file_path)
    
    # 定义支持的图片扩展名
    image_exts = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif", ".heic", ".ico"]
    
    # 遍历目录下的所有文件
    for file_name in os.listdir(dir_path):
        # 检查文件名是否包含thumbnail（不区分大小写）
        if "thumbnail" in file_name.lower():
            # 检查文件是否是图片格式
            ext = os.path.splitext(file_name)[1].lower()
            if ext in image_exts:
                # 返回完整的文件路径
                return os.path.join(dir_path, file_name)
    
    # 如果没有找到匹配的文件，返回None
    return None

def load_config(path: str):
    cfg = read_json(path) or {}
    return {
        "model": cfg.get("model"),
        "base_url": cfg.get("base_url", "http://localhost:1234/v1"),
        "provider": cfg.get("provider", "lmstudio"),
        "provider_mode": cfg.get("provider_mode", 1),
        "api_key": cfg.get("api_key", ""),
        "cloud_image_mode": (cfg.get("cloud_image_mode") or "base64"),
        "template_file": cfg.get("template_file", ""),
        "templates_by_ext": cfg.get("templates_by_ext", {}),
        "system": cfg.get("system", ""),
        "temperature": float(cfg.get("temperature", 0.7)),
        "top_p": float(cfg.get("top_p", 1.0)),
        "frequency_penalty": float(cfg.get("frequency_penalty", 0.0)),
        "presence_penalty": float(cfg.get("presence_penalty", 0.0)),
        "stop": cfg.get("stop", []),
        "max_tokens": int(cfg.get("max_tokens", 0)),
        "image_rules": cfg.get("image_rules", {}),
        "font_rules": cfg.get("font_rules", {}),
    }

def main():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lm_config.json")
    cfg = read_json(config_path) or {}
    provider_mode = cfg.get("provider_mode", 1)
    if provider_mode == 1:
        print("当前为本地模式")
    else:
        print("当前为云端模式")
    parser = argparse.ArgumentParser(prog="lm-clipboard-tag", description="剪贴板/指定路径图片生成标签并写入同目录 metadata.json")
    parser.add_argument("--config-file", default="lm_config.json", help="配置文件路径")
    parser.add_argument("--prompt", default="根据图片生成简短中文标签", help="用户提示")
    parser.add_argument("--paths", nargs='*', default=[], help="直接指定图片路径，多个用空格分隔")
    parser.add_argument("--timeout", type=float, default=120.0, help="请求超时")
    parser.add_argument("--print-output", action="store_true", help="先打印 LM Studio 输出")
    parser.add_argument("--log-dir", default="logs", help="日志保存目录")
    parser.add_argument("--retry", type=int, default=2, help="失败重试次数")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="重试间隔秒数")
    parser.add_argument("--sleep", type=float, default=0.0, help="每条处理间隔秒数")
    parser.add_argument("--max-errors", type=int, default=0, help="达到该失败数后停止，0为不限")
    parser.add_argument("--convert-on-error", action="store_true", default=True, help="当服务端拒绝格式时，回退为PNG后重试")
    args = parser.parse_args()
    cfg = load_config(args.config_file)
    # provider_mode: 1 本地 LM Studio, 2 云端 DashScope
    def to_int(x):
        try:
            return int(str(x).strip())
        except Exception:
            return None
    mode_raw = (cfg.get("provider_mode") if isinstance(cfg.get("provider_mode"), (int, str)) else None)
    prov_raw = cfg.get("provider")
    mode = None
    if mode_raw is not None:
        mode = to_int(mode_raw)
    elif isinstance(prov_raw, (int, str)) and str(prov_raw).strip() in ("1", "2"):
        mode = to_int(prov_raw)
    if mode == 1:
        effective_provider = "lmstudio"
        effective_base = cfg.get("local_base_url", "http://localhost:1234/v1")
        effective_model = cfg.get("local_model", "qwen/Qwen3-VL-4B-Instruct")
    elif mode == 2:
        effective_provider = "dashscope"
        effective_base = cfg.get("cloud_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        effective_model = cfg.get("cloud_model", "qwen-vl-max")
    else:
        effective_provider = cfg.get("provider", "lmstudio")
        effective_base = cfg.get("base_url", "http://localhost:1234/v1")
        effective_model = cfg.get("model")
    cfg_effective = dict(cfg)
    cfg_effective["provider"] = effective_provider
    cfg_effective["base_url"] = effective_base
    cfg_effective["model"] = effective_model
    system = cfg_effective.get("system", "")
    base_tpl = ""
    if not system and cfg.get("template_file") and os.path.isfile(cfg["template_file"]):
        base_tpl = read_text(cfg["template_file"])
    auth_token = get_auth_token(cfg)
    if not check_service_with_retry(cfg_effective["base_url"], min(float(args.timeout), 10.0), 3, args.retry_delay, auth_token):
        print(f"无法连接服务: {cfg_effective['base_url']} 多次重试失败，已停止")
        sys.exit(2)
    extras = {}
    if cfg.get("top_p") is not None:
        extras["top_p"] = cfg["top_p"]
    if cfg.get("frequency_penalty"):
        extras["frequency_penalty"] = cfg["frequency_penalty"]
    if cfg.get("presence_penalty"):
        extras["presence_penalty"] = cfg["presence_penalty"]
    if cfg.get("stop"):
        extras["stop"] = cfg["stop"]
    if cfg.get("max_tokens"):
        extras["max_tokens"] = cfg["max_tokens"]
    paths = []
    text = get_clipboard_text()
    paths = parse_paths(text)
    
    # 处理目录路径，查找其中的图片文件
    processed_paths = []
    for p in paths:
        if os.path.isdir(p):
            # 如果是目录，查找其中的图片文件
            for file in os.listdir(p):
                file_path = os.path.join(p, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in [
                        ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif", ".heic", ".ico"
                    ]:
                        processed_paths.append(file_path)
        else:
            processed_paths.append(p)
    
    paths = processed_paths
    if not paths:
        print("剪贴板未检测到有效路径")
        sys.exit(2)
    print("待处理路径：")
    for p in paths:
        print(p)
    total_start = time.perf_counter()
    ok = 0
    fail = 0
    if not os.path.isdir(args.log_dir):
        os.makedirs(args.log_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(args.log_dir, f"run_{ts}.json")
    entries = []
    total = len(paths)
    idx = 0
    for p in paths:
        idx += 1
        item_start = time.perf_counter()
        try:
            attempts = max(1, int(args.retry) + 1)
            out = None
            usage = None
            ext = os.path.splitext(p)[1].lower()
            remote = p.startswith("http://") or p.startswith("https://")
            
            # 检查当前标签是否为空（只检查本地文件）
            if not remote:
                d = os.path.dirname(p)
                meta_path = os.path.join(d, "metadata.json")
                before_obj = read_json(meta_path) or {}
                before_tags = before_obj.get("tags")
                if isinstance(before_tags, list) and len(before_tags) > 0:
                    print(f"[{idx}/{total}] 跳过已有标签的文件: {p}")
                    if args.sleep > 0:
                        time.sleep(float(args.sleep))
                    continue
            
            # 检查是否为已知格式
            known_extensions = [".ttf", ".otf", ".ttc", ".woff", ".woff2", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif", ".heic", ".ico"]
            
            # 对于其他格式文件，查找是否存在thumbnail图片
            thumbnail_path = None
            if ext not in known_extensions and not remote:
                thumbnail_path = find_thumbnail(p)
                print(f"检测到其他格式文件: {p}，查找thumbnail图片: {'找到' if thumbnail_path else '未找到'}")
            
            if ext in [".ttf", ".otf", ".ttc", ".woff", ".woff2"]:
                data_url = ""
            else:
                if p.startswith("http://") or p.startswith("https://"):
                    prov = (cfg_effective.get("provider") or "").strip().lower()
                    mode = (cfg.get("cloud_image_mode") or "base64").strip().lower()
                    if prov == "dashscope" and mode == "base64":
                        du = fetch_image_data_url(p, min(float(args.timeout), 15.0))
                        data_url = du if (isinstance(du, str) and du.strip()) else p
                    else:
                        data_url = p
                else:
                    # 如果存在thumbnail图片，使用thumbnail图片生成data_url
                    if thumbnail_path:
                        data_url = image_to_data_url(thumbnail_path)
                    else:
                        data_url = image_to_data_url(p)
            if ext not in [".ttf", ".otf", ".ttc", ".woff", ".woff2"]:
                mname = (cfg_effective.get("model") or "").strip()
                prov = (cfg_effective.get("provider") or "").strip().lower()
                if prov == "dashscope" and (not mname or ("vl" not in mname.lower())):
                    cfg_effective["model"] = "Qwen3 - VL"
            for k in range(attempts):
                try:
                    local_system = system
                    if not system:
                        tpl_map = cfg.get("templates_by_ext")
                        if isinstance(tpl_map, dict):
                            override_tpl = tpl_map.get(ext)
                            if override_tpl and os.path.isfile(override_tpl):
                                local_system = read_text(override_tpl)
                            elif base_tpl:
                                local_system = base_tpl
                    if ext in [".ttf", ".otf", ".ttc", ".woff", ".woff2"]:
                        font_name_with_ext = os.path.basename(p)
                        print(f"字体名称: {font_name_with_ext}")
                        out, usage = call_lmstudio_text(cfg_effective["base_url"], cfg_effective["model"], local_system, font_name_with_ext, cfg_effective["temperature"], extras, args.timeout, auth_token)
                    else:
                        out, usage = call_lmstudio_data(cfg_effective["base_url"], cfg_effective["model"], local_system, args.prompt, data_url, cfg_effective["temperature"], extras, args.timeout, auth_token, cfg_effective.get("provider"), cfg.get("cloud_image_mode"))
                        if (not remote) and (not (isinstance(out, str) and out.strip())):
                            try:
                                buf = io.BytesIO()
                                img = Image.open(p)
                                if img.mode not in ("RGB", "RGBA"):
                                    img = img.convert("RGB")
                                img.save(buf, format="PNG")
                                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                                data_url = f"data:image/png;base64,{b64}"
                                out, usage = call_lmstudio_data(cfg_effective["base_url"], cfg_effective["model"], local_system, args.prompt, data_url, cfg_effective["temperature"], extras, args.timeout, auth_token, cfg_effective.get("provider"), cfg.get("cloud_image_mode"))
                            except Exception:
                                pass
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 400:
                        try:
                            buf = io.BytesIO()
                            img = Image.open(p)
                            if img.mode not in ("RGB", "RGBA"):
                                img = img.convert("RGB")
                            img.save(buf, format="PNG")
                            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                            data_url = f"data:image/png;base64,{b64}"
                            continue
                        except Exception:
                            pass
                    if k < attempts - 1:
                        time.sleep(float(args.retry_delay))
                    else:
                        raise
                except urllib.error.URLError as e:
                    print(f"无法连接服务: {cfg_effective['base_url']} {e}")
                    ok_conn = False
                    for n in range(3):
                        time.sleep(float(args.retry_delay))
                        if check_service(cfg_effective["base_url"], min(float(args.timeout), 10.0), auth_token):
                            ok_conn = True
                            break
                    if not ok_conn:
                        print("重试3次仍无法连接，已停止")
                        sys.exit(2)
                    else:
                        continue
                except Exception:
                    if k < attempts - 1:
                        time.sleep(float(args.retry_delay))
                    else:
                        raise
            if ext in [".ttf", ".otf", ".ttc", ".woff", ".woff2"] or args.print_output:
                print(out)
            if remote:
                incoming_tags = dedup_tags(extract_tags_from_text(out))
                item_cost = time.perf_counter() - item_start
                s_usage = format_usage(usage)
                warn_empty = False
                if not (isinstance(out, str) and out.strip()) and len(incoming_tags) == 0:
                    warn_empty = True
                    print("警告：接口返回空内容（远程URL），建议更换视觉模型或检查图片链接可访问性。")
                print(f"[{idx}/{total}] 已处理远程图片: {p}，耗时 {item_cost:.2f}s" + (f"，{s_usage}" if s_usage else ""))
                if warn_empty:
                    fail += 1
                else:
                    ok += 1
                entries.append({
                    "path": p,
                    "remote": True,
                    "model_output": out,
                    "incoming_tags": incoming_tags,
                    "usage": usage,
                    "attempts": attempts,
                    "cost_seconds": round(item_cost, 3)
                })
                
                # 更新历史标签记录
                update_history_tags(incoming_tags)
                
                continue
            d = os.path.dirname(p)
            meta_path = os.path.join(d, "metadata.json")
            if os.path.exists(meta_path):
                bak_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bak")
                os.makedirs(bak_dir, exist_ok=True)
                info_dir_name = os.path.basename(d)
                backup_file_name = f"{info_dir_name}.json"
                backup_path = os.path.join(bak_dir, backup_file_name)
                shutil.copy2(meta_path, backup_path)
            before_obj = read_json(meta_path) or {}
            before_tags = before_obj.get("tags")
            item_cost = time.perf_counter() - item_start
            if ext in [".ttf", ".otf", ".ttc", ".woff", ".woff2"]:
                if os.path.isfile(p):
                    meta_path, orig_tags, final_tags = update_font_metadata(p, out, cfg.get("font_rules", {}))
                    s_usage = format_usage(usage)
                    print(f"[{idx}/{total}] 已写入: {meta_path}，耗时 {item_cost:.2f}s" + (f"，{s_usage}" if s_usage else ""))
                    ok += 1
                    entries.append({
                        "path": p,
                        "metadata": meta_path,
                        "font_name": os.path.basename(p),
                        "model_output": out,
                        "original_tags": orig_tags,
                        "final_tags": final_tags,
                        "usage": usage,
                        "attempts": attempts,
                        "cost_seconds": round(item_cost, 3)
                    })
                else:
                    print(f"[{idx}/{total}] 已处理字体: {p}，耗时 {item_cost:.2f}s")
                    ok += 1
                    entries.append({
                        "path": p,
                        "font_name": os.path.basename(p),
                        "model_output": out,
                        "attempts": attempts,
                        "cost_seconds": round(item_cost, 3)
                    })
                continue
            meta_path, orig_tags, final_tags = update_tags_json(p, out, cfg.get("image_rules", {}))
            incoming_tags = dedup_tags(extract_tags_from_text(out))
            s_usage = format_usage(usage)
            warn_empty = False
            if not (isinstance(out, str) and out.strip()) and len(incoming_tags) == 0:
                warn_empty = True
                print("警告：接口返回空内容，未提取到标签。建议使用公网图片URL或更换视觉模型。")
            print(f"[{idx}/{total}] 已写入: {meta_path}，耗时 {item_cost:.2f}s" + (f"，{s_usage}" if s_usage else ""))
            if warn_empty:
                fail += 1
            else:
                ok += 1
            entries.append({
                "path": p,
                "metadata": meta_path,
                "original_tags": [clean_tag(x) for x in (before_tags if isinstance(before_tags, list) else []) if isinstance(x, str) and clean_tag(x) and not is_bad_tag(clean_tag(x))],
                "model_output": out,
                "incoming_tags": incoming_tags,
                "final_tags": final_tags,
                "usage": usage,
                "warning": "empty_output" if warn_empty else "",
                "attempts": attempts,
                "cost_seconds": round(item_cost, 3)
            })
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                body = ""
            print(f"HTTP 错误 {e.code}: {body}")
            fail += 1
            entries.append({
                "path": p,
                "error": f"HTTP {e.code}",
                "detail": body
            })
        except Exception as e:
            print(f"错误: {e}")
            fail += 1
            entries.append({
                "path": p,
                "error": str(e)
            })
        if args.sleep > 0:
            time.sleep(float(args.sleep))
        if args.max_errors and fail >= int(args.max_errors):
            print(f"达到失败上限 {args.max_errors}，提前结束")
            break
    total_cost = time.perf_counter() - total_start
    print(f"完成：成功 {ok}，失败 {fail}，总耗时 {total_cost:.2f}s")
    sum_prompt = 0
    sum_completion = 0
    sum_total = 0
    sum_input = 0
    sum_output = 0
    for e in entries:
        u = e.get("usage") or {}
        if isinstance(u.get("prompt_tokens"), int):
            sum_prompt += u.get("prompt_tokens")
        if isinstance(u.get("completion_tokens"), int):
            sum_completion += u.get("completion_tokens")
        if isinstance(u.get("total_tokens"), int):
            sum_total += u.get("total_tokens")
        if isinstance(u.get("input_tokens"), int):
            sum_input += u.get("input_tokens")
        if isinstance(u.get("output_tokens"), int):
            sum_output += u.get("output_tokens")


    summary = {
        "timestamp": ts,
        "success": ok,
        "failed": fail,
        "total_seconds": round(total_cost, 3),
        "entries": entries,
        "usage_total": {
            "prompt_tokens": sum_prompt,
            "completion_tokens": sum_completion,
            "total_tokens": sum_total or (sum_input + sum_output),
            "input_tokens": sum_input,
            "output_tokens": sum_output
        }
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"日志: {log_path}")
    if fail > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

