import json
import os

# 使用绝对路径确保操作正确的文件
script_dir = os.path.dirname(os.path.abspath(__file__))
history_tags_path = os.path.join(script_dir, 'history_tags.json')

# ==========================
# 只需修改此列表即可定义要删除的匹配词条
# ==========================
FILTER_LIST = [
    # 括号
    '(', ')', '（', '）',
    
    # 日本姓氏
    '佐藤', '铃木', '高桥', '田中', '渡边', '伊藤', '山本', '中村', '小林', '斋藤',
    '原田', '加藤', '齐藤', '工藤', '吉田', '松本', '井上', '木村', '林', '清水',
    
    # 其他示例：可以根据需要添加或删除词条
    '约翰','cos','ー', '穴', 'あ','い','う','え','お','ア','イ','ウ','エ','オ'
]


def should_filter_tag(tag):
    """判断标签是否需要被过滤（包含过滤列表中任何字符串即删除）"""
    if not tag:
        return False
    tag_lower = tag.lower()
    return any(item.lower() in tag_lower for item in FILTER_LIST)


def main():
    """主函数"""
    try:
        # 读取history_tags.json文件
        with open(history_tags_path, 'r', encoding='utf-8') as f:
            history_tags = json.load(f)
        
        # 过滤标签
        cleaned_tags = []
        for tag in history_tags:
            if not should_filter_tag(tag):
                cleaned_tags.append(tag)
        
        # 写入过滤后的标签
        with open(history_tags_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_tags, f, ensure_ascii=False, indent=2)
        
        # 打印清理结果
        print("=" * 50)
        print("历史标签清理结果")
        print("=" * 50)
        print(f"清理前标签总数：{len(history_tags)}")
        print(f"清理后标签总数：{len(cleaned_tags)}")
        print(f"删除的标签数：{len(history_tags) - len(cleaned_tags)}")
        print("=" * 50)
        print("清理完成！")
        
    except Exception as e:
        print(f"清理过程中发生错误：{e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())