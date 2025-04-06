    # utils.py

import configparser, json
from dateutil.parser import parse, ParserError
from datetime import datetime, timezone, timedelta
from file_ops import check_dictionary_format, add_category



def process_transaction_input(user_id, parts):
    subcategory = " ".join(parts[:-1])
    category = None
    subcat_to_cat_file = f"user_data/{user_id}/dictionary_{user_id}.json"
    subcat_to_cat = read_subcat_to_cat_from_file(subcat_to_cat_file, user_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    if len(parts) > 2:
        #print(parts[0][0] , type(parts[0][0]))
        #print (parts[0][0].isdigit() , parts[0][-1].isdigit())
        if parts[0][0].isdigit() and parts[0][-1].isdigit():
            try:
                timestamp = toDateUtc(parts[0])
            except Exception as e:
                print(e)
            if len(parts) > 3:
                category = parts[1]
                subcategory = parts[2]
            else:
                subcategory = parts[1]
                category = subcat_to_cat.get(subcategory, None)
        else:
            category = parts[0]
            subcategory = parts[1]
            add_category(user_id, category, subcategory)
    else:
        category = None
        subcategory = parts[0]

    category = category or subcat_to_cat.get(subcategory, None)
    if category is None:
        category = "other"
        # Set a flag to indicate that the category needs to be chosen by the user
        unknown_cat = True
    else:
        unknown_cat = False

    # subcategory = subcategory or "other"

    return timestamp, category, subcategory, unknown_cat


def process_income_input(user_id, parts):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    category = "salary"
    if len(parts) == 3:
        try:
            timestamp = parse(parts[0], dayfirst=True)
            category = parts[1]
        except (ValueError, ParserError):
            category = parts[0]
    elif len(parts) == 2:
        try:
            timestamp = parse(parts[0], dayfirst=True)
        except (ValueError, ParserError):
            category = parts[0]

    return timestamp, category


def toDateUtc(mdate):
    # Assuming your date string is in the format 'dd.mm'
    date_string = mdate
    current_year = datetime.now().year

    # Parse the date string and add the current year
    date_obj = datetime.strptime(f"{current_year}-{date_string}", "%Y-%d.%m")

    # Set the timezone to UTC and convert it to the desired format
    date_obj_utc = date_obj.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    return date_obj_utc


def read_subcat_to_cat_from_file(file_path, user_id):

    check_dictionary_format(user_id)
    # Get user's language
    config = configparser.ConfigParser()
    config.read(f"user_data/{user_id}/config.ini")
    user_language = config.get("DEFAULT", "language")

    with open(file_path, "r") as file:
        try:
            all_dicts = json.load(file)
        except json.JSONDecodeError:
            return None

    cat_dict = all_dicts.get(user_language, {})

    # Transpose the dictionary to subcategory:category
    subcat_to_cat = {}
    for category, subcategories in cat_dict.items():
        for subcategory in subcategories:
            subcat_to_cat[subcategory] = category

    return subcat_to_cat


# def parse_input(parts, subcat_to_cat):

#     timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
#     if len(parts) > 2:
#         if parts[0][0].isdigit() and parts[0][-1].isdigit():
#             timestamp = toDateUtc(parts[0])
#             if len(parts) > 3:
#                 category = parts[1]
#                 subcategory = parts[2]
#             else:
#                 subcategory = parts[1]
#                 category = subcat_to_cat.get(subcategory, "other")
#         else:
#             category = parts[0]
#             subcategory = parts[1]
#     else:
#         category = None
#         subcategory = parts[0]

#     category = category or subcat_to_cat.get(subcategory, "other")
#     subcategory = subcategory or "other"

#     return timestamp, category, subcategory
