import os, shutil, configparser, csv, time, pandas as pd, json, datetime

from pandas_ops import (
    show_sum_per_cat, 
    show_av_per_day,
    show_total,
    get_exchange_rate,
    get_user_currency,
    recalculate_currency,
    show_last_month_sum_per_cat,
    show_last_month_av_per_day,
    show_last_month_total,
)


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


def read_config(user_id: str) -> str:
    config_path = f"user_data/{user_id}/config.ini"
    config = configparser.ConfigParser()
    config.read(config_path)

    #language = config.get("DEFAULT", "language", fallback="en")
    name = config.get('DEFAULT', 'name', fallback=None)
    currency = config.get('DEFAULT', 'currency', fallback=None)
    language = config.get('DEFAULT', 'language', fallback=None)
    limit = config.getfloat('DEFAULT', 'monthly_limit', fallback=None)
    return name,currency,language,limit


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
        writer.writerow([user_id, username, tg_username, datetime.datetime.now()])


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

    # Try to interpret record_num as ID first
    try:
        record_id = int(record_num)
        
        # Read the file using pandas
        df = pd.read_csv(records_file)
        
        # Check if 'id' column exists (new format)
        if 'id' in df.columns:
            # Delete by ID
            if record_id in df['id'].values:
                df = df[df['id'] != record_id]
                df.to_csv(records_file, index=False)
                return True
            else:
                # If ID not found, fallback to deleting by position (legacy behavior)
                with open(records_file, "r") as file:
                    lines = file.readlines()
                
                if len(lines) >= record_num:
                    del lines[-record_num]
                    with open(records_file, "w") as file:
                        file.writelines(lines)
                    return True
                else:
                    return False
        else:
            # Old format - delete by position
            with open(records_file, "r") as file:
                lines = file.readlines()
            
            if len(lines) >= record_num:
                del lines[-record_num]
                with open(records_file, "w") as file:
                    file.writelines(lines)
                return True
            else:
                return False
    
    except (ValueError, pd.errors.EmptyDataError):
        # If record_num is not a valid integer or file is empty, use legacy behavior
        with open(records_file, "r") as file:
            lines = file.readlines()

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


def backup_charts(user_id, image_paths):
    # If image_paths is a single string, convert it to a list
    if isinstance(image_paths, str):
        image_paths = [image_paths]

    # Check if backup directory exists, create if it does not
    backup_dir = f"user_data/{user_id}/backups_charts"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Backup each file in the image_paths list
    timestamp = time.strftime("%d_%m_%Y_%H_%M_%S")
    for image_path in image_paths:
        # Check if image_path is just a filename and construct the full path if needed
        if not os.path.dirname(image_path):
            image_path = f"user_data/{user_id}/{image_path}"
        filename = os.path.basename(image_path)
        backup_file = f"{backup_dir}/{filename}_{timestamp}_backup.jpg"
        shutil.copy(image_path, backup_file)

    print("Chart backup success")


def get_latest_records(user_id, record_num_or_category):
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    records = pd.DataFrame()  # Initialize records as an empty DataFrame
    if os.path.exists(records_file):
        df = pd.read_csv(records_file)[::-1].reset_index(drop=True)
        #change dataset to local currency
        exchange_rates = get_exchange_rate()
        currency = get_user_currency(user_id)

        # Make sure 'id' column exists and is in the right format
        if 'id' not in df.columns:
            # Handle old format files
            if 'user_id' not in df.columns:
                # This is really old format - create new ids
                df['id'] = df.index + 1
                df['user_id'] = user_id
                # Save the updated dataframe with IDs
                df_original = df[::-1]  # Revert to original order
                df_original.to_csv(records_file, index=False)
                df = df_original[::-1].reset_index(drop=True)  # Revert back for processing
            else:
                # Edge case - has user_id but no id
                df['id'] = df.index + 1
                df_original = df[::-1]
                df_original.to_csv(records_file, index=False)
                df = df_original[::-1].reset_index(drop=True)
            
        # No longer need to create an index column as we'll use the ID
        df = df[::-1]
        try:
            record_num = int(record_num_or_category)
            records = df.tail(record_num)
            records = recalculate_currency(records, currency, exchange_rates)
            total_amount = records["amount_cr_currency"].sum()

        except ValueError:
            category = record_num_or_category
            records = df[df["category"] == category]
            records = recalculate_currency(records, currency, exchange_rates)
            total_amount = records["amount_cr_currency"].sum()
        if records.empty:
            return None, total_amount

    records_list = records.apply(
        lambda x: f"{x['id']}: {x['timestamp']}, {x['category']}, {x['subcategory']}, {x['amount_cr_currency']}, {currency}",
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
    #print("start GetRecords executed")

    sum_per_cat = show_sum_per_cat(user_id, file_path)
    #print("GetRecords executed, sum_per_cat = ", sum_per_cat)

    av_per_day, total_av_per_day, prediction, comparison = show_av_per_day(
        user_id, file_path
    )
    #print("GetRecords executed, show_av_per_day = ", av_per_day)

    total_spendings = show_total(user_id, file_path)
    print("GetRecords executed")
    return (
        sum_per_cat,
        av_per_day,
        total_spendings,
        total_av_per_day,
        prediction,
        comparison,
    )


def get_last_month_records(user_id, command):
    if command == "show_income":
        file_path = f"user_data/{user_id}/income_{user_id}.csv"
    else:
        file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    if not os.path.exists(file_path):
        return None
    
    sum_per_cat = show_last_month_sum_per_cat(user_id, file_path)
    
    av_per_day, total_av_per_day, prediction, comparison = show_last_month_av_per_day(
        user_id, file_path
    )
    
    total_spendings = show_last_month_total(user_id, file_path)
    print("GetLastMonthRecords executed")
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
    
    # Check if 'id' field actually contains the user_id (transition case)
    if 'id' in transaction_data and str(transaction_data['id']) == str(user_id):
        # This is the old pattern - move value to user_id
        transaction_data['user_id'] = transaction_data['id']
        # Remove the id so we'll generate a new one
        del transaction_data['id']
    
    # Make sure we have a user_id field in the transaction data
    if 'user_id' not in transaction_data:
        transaction_data['user_id'] = user_id
    
    # Generate a unique transaction ID if not provided
    if 'id' not in transaction_data or not transaction_data['id']:
        # Read existing file to get the next ID
        next_id = 1
        if os.path.exists(spendings_file):
            try:
                df = pd.read_csv(spendings_file)
                if 'id' in df.columns and not df['id'].empty:
                    # Get the maximum ID and increment by 1
                    max_id = df['id'].max()
                    if pd.notna(max_id):
                        next_id = int(max_id) + 1
            except Exception as e:
                print(f"Error determining next transaction ID: {e}")
        
        transaction_data['id'] = next_id
        
    if not os.path.exists(spendings_file):
        with open(spendings_file, "w", newline="") as csvfile:
            fieldnames = [
                "id",
                "timestamp",
                "category",
                "subcategory",
                "amount",
                "currency",
                "user_id",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    else:
        # Check if file needs to be updated to new structure
        with open(spendings_file, 'r') as f:
            header = f.readline().strip().split(',')
        
        # If the file is in old format, update it first
        if 'user_id' not in header and 'id' in header:
            update_spendings_file_structure(user_id)

    with open(spendings_file, "a", newline="") as csvfile:
        fieldnames = [
            "id",
            "timestamp",
            "category",
            "subcategory",
            "amount",
            "currency",
            "user_id",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(transaction_data)


def save_user_income(user_id, transaction_data):
    user_dir = f"user_data/{user_id}"
    income_file = f"{user_dir}/income_{user_id}.csv"
    
    # Check if 'id' field actually contains the user_id (transition case)
    if 'id' in transaction_data and str(transaction_data['id']) == str(user_id):
        # This is the old pattern - move value to user_id
        transaction_data['user_id'] = transaction_data['id']
        # Remove the id so we'll generate a new one
        del transaction_data['id']
    
    # Make sure we have a user_id field
    if 'user_id' not in transaction_data:
        transaction_data['user_id'] = user_id
    
    # Generate a unique transaction ID if not provided
    if 'id' not in transaction_data or not transaction_data['id']:
        # Read existing file to get the next ID
        next_id = 1
        if os.path.exists(income_file):
            try:
                df = pd.read_csv(income_file)
                if 'id' in df.columns and not df['id'].empty:
                    # Get the maximum ID and increment by 1
                    max_id = df['id'].max()
                    if pd.notna(max_id):
                        next_id = int(max_id) + 1
            except Exception as e:
                print(f"Error determining next income ID: {e}")
        
        transaction_data['id'] = next_id

    if not os.path.exists(income_file):
        with open(income_file, "w", newline="") as csvfile:
            fieldnames = [
                "id",
                "timestamp",
                "category",
                "amount",
                "currency",
                "user_id",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    else:
        # Check if file needs to be updated to new structure
        with open(income_file, 'r') as f:
            header = f.readline().strip().split(',')
        
        # If the file is in old format, update it first
        if 'user_id' not in header and 'id' in header:
            update_income_file_structure(user_id)

    with open(income_file, "a", newline="") as csvfile:
        fieldnames = [
            "id",
            "timestamp",
            "category",
            "amount",
            "currency",
            "user_id",
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

def check_log(record_num):
    filepath = "user_data/global_log.txt"
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
        
        # Get the last record_num lines
        last_lines = lines[-record_num:] if record_num < len(lines) else lines
        
        # Join the lines into a single string
        log_content = ''.join(last_lines)
        
        return log_content if log_content else "No log entries found."
    except FileNotFoundError:
        return "Log file not found."
    except Exception as e:
        return f"Error reading log file: {str(e)}"

def get_frequently_used_categories(user_id, limit=10):
    """Get recently used categories for a user, ordered by most recent first."""
    file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    if not os.path.exists(file_path):
        return []
    
    try:
        df = pd.read_csv(file_path)
        if df.empty or 'category' not in df.columns or 'timestamp' not in df.columns:
            return []
        
        # Convert timestamp to datetime for proper sorting
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Get categories sorted by recency (most recent first)
        categories = df.sort_values(by='timestamp', ascending=False)['category'].head(limit).unique().tolist()
        print
        return categories
    except Exception as e:
        print(f"Error getting recently used categories: {e}")
        return []

def get_frequently_used_subcategories(user_id, category, limit=10):
    """Get frequently used subcategories for a specific category, ordered by frequency."""
    file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    if not os.path.exists(file_path):
        return []
    
    try:
        df = pd.read_csv(file_path)
        if df.empty or 'category' not in df.columns or 'subcategory' not in df.columns:
            return []
        
        # Filter by category and get subcategories sorted by frequency
        category_df = df[df['category'] == category]
        subcategories = category_df['subcategory'].value_counts().head(limit).index.tolist()
        return subcategories
    except Exception as e:
        print(f"Error getting frequently used subcategories: {e}")
        return []

def get_recent_amounts(user_id, subcategory, limit=5):
    """Get recent transaction amounts for a specific subcategory."""
    file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    if not os.path.exists(file_path):
        return []
    
    try:
        df = pd.read_csv(file_path)
        if df.empty or 'subcategory' not in df.columns or 'amount' not in df.columns:
            return []
        
        # Filter by subcategory, sort by timestamp (most recent first) and get amounts
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        subcategory_df = df[df['subcategory'] == subcategory].sort_values(by='timestamp', ascending=False)
        amounts = subcategory_df['amount'].head(limit).tolist()
        return amounts
    except Exception as e:
        print(f"Error getting recent amounts: {e}")
        return []

def ensure_transaction_ids(user_id):
    """Check if all transactions have IDs and add them if missing"""
    spendings_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    if not os.path.exists(spendings_file):
        return False
    
    try:
        # Read the CSV file
        df = pd.read_csv(spendings_file)
        
        # Check if ID column exists
        id_column_missing = 'id' not in df.columns
        
        # Check if any IDs are missing
        if id_column_missing:
            # Add ID column
            df['id'] = range(1, len(df) + 1)
            df.to_csv(spendings_file, index=False)
            print(f"Added ID column to transactions for user {user_id}")
            return True
        elif df['id'].isna().any():
            # Fill in missing IDs
            # Get the highest existing ID
            max_id = df['id'].max()
            if pd.isna(max_id):
                max_id = 0
            
            # Assign new IDs to rows with missing IDs
            next_id = int(max_id) + 1
            for index, row in df.iterrows():
                if pd.isna(row['id']):
                    df.at[index, 'id'] = next_id
                    next_id += 1
            
            df.to_csv(spendings_file, index=False)
            print(f"Filled in missing IDs for user {user_id}")
            return True
            
        return False
    except Exception as e:
        print(f"Error ensuring transaction IDs: {e}")
        return False

def update_spendings_file_structure(user_id):
    """
    Updates the structure of a user's spendings file to the new format:
    - Changes columns from timestamp,category,subcategory,amount,currency,id
    - To id,timestamp,category,subcategory,amount,currency,user_id
    - Old id column becomes user_id
    - New id column represents transaction count number
    """
    spendings_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    
    # Check if file exists
    if not os.path.exists(spendings_file):
        return {"success": False, "message": "Spendings file not found."}
    
    try:
        # Back up the file before making changes
        backup_spendings(user_id, spendings_file)
        
        # Read the CSV file
        df = pd.read_csv(spendings_file)
        
        # Check if the file is already in the new format
        if 'user_id' in df.columns and 'id' in df.columns and df.columns[0] == 'id':
            return {"success": False, "message": "File already in new format."}
        
        # Handle old format with 'id' as the user ID
        if 'id' in df.columns and 'user_id' not in df.columns:
            # Rename the existing 'id' column to 'user_id'
            df = df.rename(columns={'id': 'user_id'})
        elif 'user_id' not in df.columns:
            # If there's no id column or user_id column, create user_id column with user's ID
            df['user_id'] = user_id
        
        # Check if there's already an 'id' column (which would now be a transaction ID)
        if 'id' not in df.columns:
            # Add a new 'id' column as transaction count (starting from 1)
            df.insert(0, 'id', range(1, len(df) + 1))
        
        # Ensure column order is correct
        column_order = ['id', 'timestamp', 'category', 'subcategory', 'amount', 'currency', 'user_id']
        # Get only the columns that exist in the DataFrame
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        # Save the updated DataFrame back to the file
        df.to_csv(spendings_file, index=False)
        
        return {"success": True, "message": f"Successfully updated {len(df)} transactions to new format."}
    
    except Exception as e:
        return {"success": False, "message": f"Error updating file structure: {str(e)}"}

def update_income_file_structure(user_id):
    """
    Updates the structure of a user's income file to the new format:
    - Changes columns from timestamp,category,amount,currency
    - To id,timestamp,category,amount,currency,user_id
    - Adds transaction IDs and user_id
    """
    income_file = f"user_data/{user_id}/income_{user_id}.csv"
    
    # Check if file exists
    if not os.path.exists(income_file):
        return {"success": False, "message": "Income file not found."}
    
    try:
        # Back up the file before making changes
        backup_spendings(user_id, income_file)
        
        # Read the CSV file
        df = pd.read_csv(income_file)
        
        # Check if the file is already in the new format
        if 'user_id' in df.columns and 'id' in df.columns and df.columns[0] == 'id':
            return {"success": False, "message": "File already in new format."}
        
        # Add user_id column if it doesn't exist
        if 'user_id' not in df.columns:
            df['user_id'] = user_id
        
        # Add id column if it doesn't exist
        if 'id' not in df.columns:
            # Add a new 'id' column as transaction count (starting from 1)
            df.insert(0, 'id', range(1, len(df) + 1))
        
        # Ensure column order is correct
        column_order = ['id', 'timestamp', 'category', 'amount', 'currency', 'user_id']
        # Get only the columns that exist in the DataFrame
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        # Save the updated DataFrame back to the file
        df.to_csv(income_file, index=False)
        
        return {"success": True, "message": f"Successfully updated {len(df)} income records to new format."}
    
    except Exception as e:
        return {"success": False, "message": f"Error updating income file structure: {str(e)}"}

# Function to update all existing files to the new structure
def migrate_all_user_files_to_new_structure():
    """
    Migrates all existing user files to the new data structure.
    This can be run once to update all user files in the system.
    """
    results = []
    
    # Check if user_data directory exists
    if not os.path.exists("user_data"):
        return {"success": False, "message": "No user data directory found."}
    
    # Get all user directories
    user_dirs = [d for d in os.listdir("user_data") if os.path.isdir(f"user_data/{d}") and d != "Deleted"]
    
    for user_id in user_dirs:
        user_result = {"user_id": user_id, "spendings": None, "income": None}
        
        # Update spendings file
        spendings_file = f"user_data/{user_id}/spendings_{user_id}.csv"
        if os.path.exists(spendings_file):
            result = update_spendings_file_structure(user_id)
            user_result["spendings"] = result
        
        # Update income file
        income_file = f"user_data/{user_id}/income_{user_id}.csv"
        if os.path.exists(income_file):
            result = update_income_file_structure(user_id)
            user_result["income"] = result
        
        results.append(user_result)
    
    return {"success": True, "message": f"Processed {len(results)} user directories", "details": results}

