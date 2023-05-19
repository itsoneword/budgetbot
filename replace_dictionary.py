import os
import shutil

# Path to the default dictionary file
default_dict_path = "configs/dictionary.txt"

# Path to the users' data directory
users_data_dir = "user_data"

# Iterate over each subdirectory in the users' data directory
for user_id in os.listdir(users_data_dir):
    user_dir = os.path.join(users_data_dir, user_id)

    # Skip files and non-directory entries
    if not os.path.isdir(user_dir):
        continue

    # Path to the user's dictionary file
    user_dict_path = os.path.join(user_dir, f"dictionary_{user_id}.txt")

    # If a dictionary file already exists for this user, back it up
    if os.path.isfile(user_dict_path):
        # Create a backup directory if it doesn't exist
        backup_dir = os.path.join(user_dir, "backup")
        os.makedirs(backup_dir, exist_ok=True)

        # Move the existing dictionary file to the backup directory
        backup_dict_path = os.path.join(backup_dir, f"dictionary_{user_id}_backup.txt")
        shutil.move(user_dict_path, backup_dict_path)

    # Copy the default dictionary file to the user's directory
    shutil.copy(default_dict_path, user_dict_path)

print("Dictionaries updated.")
