import os
import importlib
import configparser

def get_user_language(user_id):
    """Get the language setting for a user from their config file"""
    config = configparser.ConfigParser()
    config_path = f"user_data/{user_id}/config.ini"
    
    if not os.path.exists(config_path):
        return "en"  # Default to English
    
    config.read(config_path)
    language = config.get("DEFAULT", "language", fallback="en")  # Fallback to 'en' if not set
    return language

def check_language(update, context):
    """Check the language setting for the current user and return the appropriate texts module"""
    if update and update.effective_user:
        user_id = str(update.effective_user.id)
        language = get_user_language(user_id)
        #print("DEBUG: Language is", language)
        # Dynamically import the correct texts module based on language
        if language == "ru":
            texts_module = importlib.import_module("texts_ru")
        else:
            texts_module = importlib.import_module("texts")
        #print("DEBUG: Texts module is", texts_module)
        return texts_module
    else:
        # Default to English if update or user is None
        #print("DEBUG: update or user is None, defaulting to English texts")
        #print("DEBUG: update =", update)
        return importlib.import_module("texts") 