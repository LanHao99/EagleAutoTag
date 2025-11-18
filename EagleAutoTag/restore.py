import os
import shutil
import sys
import subprocess

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

def parse_paths(text: str):
    return [p.strip() for p in text.splitlines() if p.strip() and os.path.exists(p.strip())]

def main():
    bak_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bak")
    if not os.path.isdir(bak_dir):
        print(f"Backup directory '{bak_dir}' not found.")
        sys.exit(1)

    clipboard_text = get_clipboard_text()
    if not clipboard_text:
        print("Clipboard is empty.")
        sys.exit(1)

    paths = parse_paths(clipboard_text)
    if not paths:
        print("No valid paths found in clipboard.")
        sys.exit(1)

    print("Paths to restore:")
    for p in paths:
        print(p)

    restored_count = 0
    for path in paths:
        info_dir = os.path.dirname(path)
        info_dir_name = os.path.basename(info_dir)
        backup_file_name = f"{info_dir_name}.json"
        backup_path = os.path.join(bak_dir, backup_file_name)
        target_path = os.path.join(info_dir, "metadata.json")

        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, target_path)
                print(f"Restored: {target_path}")
                restored_count += 1
            except Exception as e:
                print(f"Failed to restore {target_path}: {e}")
        else:
            print(f"Backup not found for {path} (expected: {backup_path})")

    print(f"\nRestore complete. {restored_count} file(s) restored.")

if __name__ == "__main__":
    main()