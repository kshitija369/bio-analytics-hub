import os
import re

# Terminology Translation Map
RENAME_MAP = {
    "Peak Autonomic Recovery": "Peak Autonomic Recovery",
    "BiometricDatabase": "BiometricDatabase",
    "BiometricNormalizer": "BiometricNormalizer",
    "BiometricProvider": "BiometricProvider",
    "Bio_Analytics_Hub": "Bio_Analytics_Hub",
    "Biometric": "Biometric",
    "biometric_log": "biometric_log",
    "biometric": "biometric",
    "BIOMETRIC": "BIOMETRIC",
    "NAR": "NAR",
    "nar": "nar",
}

# Import Refactors
IMPORT_REPLACE = {
    r"app\.providers": "app.adapters",
    r"from \.dimension_repository import DimensionRepository": "from app.domain.dimension_repository import DimensionRepository",
}

def refactor_file(file_path):
    if os.path.isdir(file_path):
        return
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    new_content = content
    
    # Apply terminology translation
    for old, new in RENAME_MAP.items():
        new_content = new_content.replace(old, new)
        
    # Apply import refactors
    for pattern, replacement in IMPORT_REPLACE.items():
        new_content = re.sub(pattern, replacement, new_content)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False

def main():
    extensions = {".py", ".yaml", ".md", ".sh", ".html"}
    for root, dirs, files in os.walk("."):
        if ".git" in dirs:
            dirs.remove(".git")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                if refactor_file(file_path):
                    print(f"Refactored: {file_path}")

if __name__ == "__main__":
    main()
