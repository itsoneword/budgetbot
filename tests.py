import pandas as pd

df = pd.read_csv("user_data/46304833/spendings_46304833.csv")
# Assuming df is your DataFrame and 'category' is the column with categories
top_5_categories = df["category"].value_counts().nlargest(5)

print(top_5_categories)
