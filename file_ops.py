import os, shutil, configparser, csv, time, pandas as pd, json, datetime

from pandas_ops import show_sum_per_cat, show_av_per_day, show_total


async def archive_user_data(user_id: str):
    user_data_dir = f"user_data/{user_id}"

    # Check if user data directory exists
    if not os.path.exists(user_data_dir):
        return "No user data found."

    # Create Deleted directory if it doesn't exist
    deleted_dir = "user_data/Deleted"
    os.makedirs(deleted_dir, exist_ok=True)

    # Create a timestamp
    timestamp = time.strftime("%d_%m_%Y_%H_%M_%S")

    # Move the user's directory to the Deleted directory
    shutil.move(user_data_dir, f"{deleted_dir}/{user_id}_{timestamp}")

    return "Your data has been deleted."


def read_config(user_id: str, section: str, key: str) -> str:
    config_path = f"user_data/{user_id}/config.ini"
    config = configparser.ConfigParser()
    config.read(config_path)
    return config.get(section, key)


def update_user_list(user_id: str, username: str, tg_username: str):
    user_list_file = "user_list.csv"

    # Check if the file exists
    if not os.path.exists(user_list_file):
        with open(user_list_file, "w", newline="") as file:
            writer = csv.writer(file)
            # If the file didn't exist, we need to create the header
            writer.writerow(["User ID", "Name", "Telegram Username"])

    # Now, we'll open the file again to add the user information
    with open(user_list_file, "r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            # If the user is already in the list, we don't need to add them again
            if row[0] == user_id:
                return

    # If we got this far, the user is not in the list, so we'll add them
    with open(user_list_file, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([user_id, username, tg_username])


def record_exists(user_id):
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    return os.path.exists(records_file)


def delete_record(user_id, record_num, command):

    if command == "delete":
        # Handle the 'delete' command
        records_file = f"user_data/{user_id}/spendings_{user_id}.csv"

    elif command == "delete_income":
        # Handle the 'delete_income' command
        records_file = f"user_data/{user_id}/income_{user_id}.csv"

    backup_spendings(user_id, records_file)

    with open(records_file, "r") as file:
        lines = file.readlines()

    # Delete the specific record from the end
    if len(lines) >= record_num:
        del lines[-record_num]

        with open(records_file, "w") as file:
            file.writelines(lines)
        return True
    else:
        return False


def backup_spendings(user_id, records_file):

    # records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    # Check if backup directory exists, create if it does not
    backup_dir = f"user_data/{user_id}/backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Backup the file
    timestamp = time.strftime("%d_%m_%Y_%H_%M_%S")
    # Extract the part of the records_file string between the last '/' and the last '_'
    record_type = records_file[records_file.rfind("/") + 1 : records_file.rfind("_")]

    # Use the extracted part to create the backup file name
    backup_file = f"{backup_dir}/{record_type}_{user_id}_{timestamp}_backup.csv"
    shutil.copy(records_file, backup_file)
    print("backup success")


def backup_charts(user_id):

    image1_path = f"user_data/{user_id}/monthly_chart_{user_id}.jpg"
    image2_path = f"user_data/{user_id}/monthly_pivot_{user_id}.jpg"

    # Check if backup directory exists, create if it does not
    backup_dir = f"user_data/{user_id}/backups_charts"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Backup the file
    timestamp = time.strftime("%d_%m_%Y_%H_%M_%S")
    backup_file1 = f"{backup_dir}/monthly_chart_{user_id}_{timestamp}_backup.jpg"
    backup_file2 = f"{backup_dir}/monthly_pivot_{user_id}_{timestamp}_backup.jpg"
    shutil.copy(image1_path, backup_file1)
    shutil.copy(image2_path, backup_file2)
    print("chart backup success")


def get_latest_records(user_id, record_num_or_category):
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    records = pd.DataFrame()  # Initialize records as an empty DataFrame
    if os.path.exists(records_file):
        df = pd.read_csv(records_file)[::-1].reset_index(drop=True)
        df["index"] = df.index + 1  # Add 1 if your CSV doesn't have a header row
        df = df[::-1]
        try:
            record_num = int(record_num_or_category)
            records = df.tail(record_num)
            total_amount = records["amount"].sum()

        except ValueError:
            category = record_num_or_category
            records = df[df["category"] == category]
            total_amount = records["amount"].sum()
        if records.empty:
            return None, total_amount

    records_list = records.apply(
        lambda x: f"{x['index']}: {x['timestamp']}, {x['category']}, {x['subcategory']}, {x['amount']}, {x['currency']}",
        axis=1,
    ).tolist()

    return records_list, total_amount


def add_category(user_id, category, subcategory):
    config = configparser.ConfigParser()
    config.read(f"user_data/{user_id}/config.ini")
    user_language = config.get("DEFAULT", "language")
    check_and_copy_dictionary(user_id)

    dictionary_path = f"user_data/{user_id}/dictionary_{user_id}.json"
    with open(dictionary_path, "r") as file:
        all_dicts = json.load(file)

    cat_dict = all_dicts.get(user_language, {})

    if category not in cat_dict:
        cat_dict[category] = [subcategory]
    elif subcategory not in cat_dict[category]:
        cat_dict[category].append(subcategory)

    all_dicts[user_language] = cat_dict

    with open(dictionary_path, "w") as file:
        json.dump(all_dicts, file, ensure_ascii=False)

    update_category(user_id, subcategory, category)


def update_category(user_id, subcategory, new_category):
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    if not os.path.exists(records_file):
        return
    df = pd.read_csv(records_file)
    mask = (df["subcategory"] == subcategory) & (df["category"] == "other")
    df.loc[mask, "category"] = new_category
    df.to_csv(records_file, index=False)


def remove_category(user_id, category, subcategory):
    config = configparser.ConfigParser()
    config.read(f"user_data/{user_id}/config.ini")
    user_language = config.get("DEFAULT", "language")

    dictionary_path = f"user_data/{user_id}/dictionary_{user_id}.json"
    with open(dictionary_path, "r") as file:
        all_dicts = json.load(file)

    cat_dict = all_dicts.get(user_language, {})

    if category in cat_dict and subcategory in cat_dict[category]:
        cat_dict[category].remove(subcategory)
        if not cat_dict[
            category
        ]:  # If there are no more subcategories, remove the category
            del cat_dict[category]
    all_dicts[user_language] = cat_dict

    with open(dictionary_path, "w") as file:
        json.dump(all_dicts, file, ensure_ascii=False)


def check_dictionary_format(user_id: str):
    user_dir = f"user_data/{user_id}"
    dictionary_path = f"{user_dir}/dictionary_{user_id}.json"
    check_and_copy_dictionary(user_id)

    with open(dictionary_path, "r") as file:
        file_content = file.read()

    try:
        parsed_dict = json.loads(file_content)
        if not all(key in parsed_dict for key in ["en", "ru"]):
            raise ValueError("Dictionary is not multilingual")
    except (json.JSONDecodeError, ValueError):
        # The dictionary is in the old format or not multilingual, so we need to replace it.
        default_dict_path = "configs/dictionary.json"
        with open(default_dict_path, "r") as default_file, open(
            dictionary_path, "w"
        ) as user_dict_file:
            user_dict_file.write(default_file.read())


def read_dictionary(user_id: str) -> dict:
    config = configparser.ConfigParser()
    config.read(f"user_data/{user_id}/config.ini")
    user_language = config.get("DEFAULT", "language")

    dictionary_path = f"user_data/{user_id}/dictionary_{user_id}.json"
    with open(dictionary_path, "r") as file:
        all_dicts = json.load(file)
    cat_dict = all_dicts.get(user_language, {})

    return cat_dict


def check_config_exists(user_id):
    user_dir = f"user_data/{user_id}"
    return os.path.exists(f"{user_dir}/config.ini")


def get_records(user_id, command):

    if command == "show_income":
        file_path = f"user_data/{user_id}/income_{user_id}.csv"
    else:
        file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    if not os.path.exists(file_path):
        return None
    sum_per_cat = show_sum_per_cat(user_id, file_path)
    av_per_day, total_av_per_day, prediction, comparison = show_av_per_day(
        user_id, file_path
    )
    total_spendings = show_total(user_id, file_path)
    return (
        sum_per_cat,
        av_per_day,
        total_spendings,
        total_av_per_day,
        prediction,
        comparison,
    )


def save_user_transaction(user_id, transaction_data):
    user_dir = f"user_data/{user_id}"
    spendings_file = f"{user_dir}/spendings_{user_id}.csv"

    if not os.path.exists(spendings_file):
        with open(spendings_file, "w", newline="") as csvfile:
            fieldnames = [
                "timestamp",
                "category",
                "subcategory",
                "amount",
                "currency",
                "id",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    with open(spendings_file, "a", newline="") as csvfile:
        fieldnames = [
            "timestamp",
            "category",
            "subcategory",
            "amount",
            "currency",
            "id",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(transaction_data)


def save_user_income(user_id, transaction_data):
    user_dir = f"user_data/{user_id}"
    income_file = f"{user_dir}/income_{user_id}.csv"

    if not os.path.exists(income_file):
        with open(income_file, "w", newline="") as csvfile:
            fieldnames = [
                "timestamp",
                "category",
                "amount",
                "currency",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    with open(income_file, "a", newline="") as csvfile:
        fieldnames = [
            "timestamp",
            "category",
            "amount",
            "currency",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(transaction_data)


def save_user_setting(user_id: str, setting_key: str, setting_value: str):
    user_dir = f"user_data/{user_id}"
    create_config_file(user_id, setting_key)

    config = configparser.ConfigParser()
    config.read(f"{user_dir}/config.ini")  # Read the existing config file
    if "DEFAULT" not in config:
        config["DEFAULT"] = {}
    config["DEFAULT"][setting_key] = setting_value  # Update the setting value
    with open(f"{user_dir}/config.ini", "w") as configfile:
        config.write(configfile)


def create_config_file(user_id, user_name):
    user_dir = f"user_data/{user_id}"
    config_file_path = f"{user_dir}/config.ini"

    if not os.path.exists(config_file_path):
        config = configparser.ConfigParser()
        config["DEFAULT"] = {"ID": user_id, "NAME": user_name}
        with open(config_file_path, "w") as configfile:
            config.write(configfile)


def check_and_copy_dictionary(user_id):
    dictionary_file = f"user_data/{user_id}/dictionary_{user_id}.json"
    original_dictionary_file = "configs/dictionary.json"

    if not os.path.exists(dictionary_file):
        shutil.copyfile(original_dictionary_file, dictionary_file)


def create_user_dir_and_copy_dict(user_id):
    user_dir = f"user_data/{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    if not os.path.exists(f"{user_dir}/dictionary_{user_id}.json"):
        shutil.copy("configs/dictionary.json", f"{user_dir}/dictionary_{user_id}.json")
    return user_dir


# def save_to_file(file_path, data, mode="a"):
#     with open(file_path, mode) as file:
#         file.write(data)


# def read_from_file(file_path):
#     if os.path.exists(file_path):
#         with open(file_path, "r") as file:
#             return file.readlines()
#     else:
#         return None


# def delete_line_from_file(file_path, line_content):
#     lines = read_from_file(file_path)
#     if lines:
#         with open(file_path, "w") as file:
#             for line in lines:
#                 if line.strip("\n") != line_content:
#                     file.write(line)
# def get_records(user_id):
#     file_path = f"user_data/{user_id}/spendings_{user_id}.csv"

#     if not os.path.exists(file_path):
#         return None

#     sum_per_cat = show_sum_per_cat(user_id)
#     av_per_day = show_av_per_day(user_id)
#     total_spendings = show_total(user_id)

#     return sum_per_cat, av_per_day, total_spendings


# def update_spendings_file(user_id: str, new_spendings_data: bytes):
#     user_dir = f"user_data/{user_id}"
#     spendings_file_path = f"{user_dir}/spendings_{user_id}.csv"
#     backup_spendings(user_id)
#     # Write the new spendings data to the spendings file
#     with open(spendings_file_path, "wb") as file:
#         file.write(new_spendings_data)
