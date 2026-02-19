import os
import sys

EXCLUDE_DIRS = {'__pycache__', '.git', '.idea', '.vscode', 'venv', 'env'}


def get_package_string(root_package):
    package_paths = []
    abs_root = os.path.abspath(root_package)
    base_dir = os.path.dirname(abs_root)
    for dirpath, dirnames, filenames in os.walk(root_package):
        dirnames[:] = [
            d
            for d in dirnames if
            d not in EXCLUDE_DIRS and not d.startswith('.')
        ]
        rel_path = os.path.relpath(dirpath, base_dir)
        dot_path = rel_path.replace(os.path.sep, '.')
        package_paths.append(f"{dot_path}.*")
    return " ".join(package_paths)


if __name__ == "__main__":
    target_dir = sys.argv[1]
    result = get_package_string(target_dir)
    print(result)