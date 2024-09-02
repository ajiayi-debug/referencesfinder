import os
import hashlib

def calculate_md5(file_path):
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_file_hashes(folder_path):
    """Get a dictionary of file names and their MD5 hashes for a given folder."""
    file_hashes = {}
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_hashes[file_path] = calculate_md5(file_path)
    return file_hashes

def compare_folders(folder1, folder2):
    """Compare PDF files between two folders based on their MD5 hashes."""
    folder1_hashes = get_file_hashes(folder1)
    folder2_hashes = get_file_hashes(folder2)

    # Extract file names without path
    folder1_files = {os.path.basename(path) for path in folder1_hashes}
    folder2_files = {os.path.basename(path) for path in folder2_hashes}

    # Files that are in folder1 but not in folder2
    only_in_folder1 = folder1_files - folder2_files
    if only_in_folder1:
        print("Files in folder1 but not in folder2:")
        for file in only_in_folder1:
            print(file)

    # Files that are in folder2 but not in folder1
    only_in_folder2 = folder2_files - folder1_files
    if only_in_folder2:
        print("Files in folder2 but not in folder1:")
        for file in only_in_folder2:
            print(file)

    # Common files, check for hash matches
    common_files = folder1_files & folder2_files
    if common_files:
        print("Comparing common files...")
        for file in common_files:
            path1 = os.path.join(folder1, file)
            path2 = os.path.join(folder2, file)

            if folder1_hashes[path1] == folder2_hashes[path2]:
                print(f"{file} is identical in both folders.")
            else:
                print(f"{file} differs between folders.")

if __name__ == "__main__":
    folder1_path = 'papers'
    folder2_path = 'papers_check'

    compare_folders(folder1_path, folder2_path)
