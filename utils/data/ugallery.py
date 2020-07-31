from datetime import datetime

import pandas as pd


def get_transactions_dataframes(inventory_path, purchases_path, display_stats=False):
    date_to_timestamp = lambda t: int(datetime.strptime(t[:19], "%Y-%m-%d %H:%M:%S").timestamp())
    # Load additions DataFrame from CSV
    inventory_df = pd.read_csv(
        inventory_path,
        dtype={"id": str},  # Force item_id to be read as string
    )
    # Rename columns to a common format
    inventory_df = inventory_df.rename(columns={
        "id": "item_id",
        "upload_date": "timestamp",
    })
    # Drop unused columns
    inventory_df = inventory_df.drop(["original", "medium_id"], axis=1)
    # Transform transaction date into timestamp
    inventory_df["timestamp"] = inventory_df["timestamp"].apply(date_to_timestamp)
    # Sort trasactions by timestamp
    inventory_df = inventory_df.sort_values("timestamp")
    # Reset index according to new order
    inventory_df = inventory_df.reset_index(drop=True)
    
    # Load removals DataFrame from CSV
    purchases_df = pd.read_csv(
        purchases_path,
        dtype={"artwork_id": str},  # Force item_id to be read as string
    )
    # Rename columns to a common format
    purchases_df = purchases_df.rename(columns={
        "artwork_id": "item_id",
        "customer_id": "user_id",
        "order_date": "timestamp",
    })
    # Transform transaction date into timestamp
    purchases_df["timestamp"] = purchases_df["timestamp"].apply(date_to_timestamp)
    # Form purchases baskets and transform into list
    purchases_df = purchases_df.groupby(["timestamp", "user_id"])["item_id"].apply(list)
    # Move groupby indexes to columns (by reindexing)
    purchases_df = purchases_df.reset_index()
    # Sort transactions by timestamp
    purchases_df = purchases_df.sort_values("timestamp")
    # Reset index according to new order
    purchases_df = purchases_df.reset_index(drop=True)
    
    if display_stats:    
        for col in inventory_df.columns:
            print(f"Inventory - {col}: {inventory_df[col].nunique()}")

        for col in purchases_df.columns:
            if col != "item_id":
                print(f"Purchases - {col}: {purchases_df[col].nunique()}")
            else:
                print(f"Purchases - {col}: {purchases_df[col].map(len).mean()}")
    
    return inventory_df, purchases_df

def add_aggregation_columns(purchases_df):
    # Add column with number of baskets per user_id
    purchases_df["n_baskets"] = purchases_df.groupby("user_id")["timestamp"].transform("size")
    # Add column with size of purchase basket for each purchase
    purchases_df["n_items"] = purchases_df["item_id"].apply(len)
    # Sort transactions by timestamp
    purchases_df = purchases_df.sort_values("timestamp")
    # Reset index according to new order
    purchases_df = purchases_df.reset_index(drop=True)
    return purchases_df

def mark_evaluation_rows(interactions_df, threshold=1):
    def _mark_evaluation_rows(group):
        # Only the last 'threshold' items are used for evaluation,
        # unless less items are available (then they're used for training)
        evaluation_series = pd.Series(False, index=group.index)
        if len(group) > threshold:
            evaluation_series.iloc[-threshold:] = True
        return evaluation_series

    # Mark evaluation rows
    interactions_df["evaluation"] = interactions_df.groupby(["user_id"])["user_id"].apply(_mark_evaluation_rows)
    # Sort transactions by timestamp
    interactions_df = interactions_df.sort_values("timestamp")
    # Reset index according to new order
    interactions_df = interactions_df.reset_index(drop=True)
    return interactions_df

def get_holdout(interactions_df):
    # Create evaluation dataframe
    holdout = []
    for user_id, group in interactions_df.groupby("user_id"):
        # Check if there's a profile for training
        profile_rows = group[~group["evaluation"]]
        predict_rows = group[group["evaluation"]]
        # Extract items
        profile = profile_rows["item_id"].values.tolist()
        profile = [item for p in profile for item in p]
        # Keep last interactions for evaluation
        for _, p in predict_rows.iterrows():
            timestamp = p["timestamp"]
            predict = p["item_id"]
            holdout.append([timestamp, profile, predict, user_id])
            # profile.extend(predict)  # If profile grows in evaluation
    # Store holdout in a pandas dataframe
    holdout = pd.DataFrame(
        holdout,
        columns=["timestamp", "profile", "predict", "user_id"],
    )
    holdout = holdout.sort_values(by=["timestamp"])
    holdout = holdout.reset_index(drop=True)

    # Pick interactions not used for evaluation
    new_dataset = interactions_df[~interactions_df["evaluation"]]
    # Sort transactions by timestamp
    new_dataset = new_dataset.sort_values("timestamp")
    # Reset index according to new order
    new_dataset = new_dataset.reset_index(drop=True)

    return holdout, new_dataset

def map_ids_to_indexes(dataframe, id2index):
    # Apply mapping
    if isinstance(dataframe["item_id"].values[0], list):
        dataframe["item_id"] = dataframe["item_id"].apply(
            lambda item_ids: [id2index[_id] for _id in item_ids],
        )
    elif isinstance(dataframe["item_id"].values[0], str):
        dataframe["item_id"] = dataframe["item_id"].apply(
            lambda _id: id2index[_id],
        )
    return dataframe

def get_evaluation_dataframe(evaluation_path):
    # Load evaluation DataFrame from CSV
    evaluation_df = pd.read_csv(evaluation_path)
    string_to_list = lambda s: list(map(int, s.strip("[]").split(", ")))
    # Transform lists from str to int
    evaluation_df["shopping_cart"] = evaluation_df["shopping_cart"].apply(
        lambda s: string_to_list(s) if isinstance(s, str) else s,
    )
    evaluation_df["profile"] = evaluation_df["profile"].apply(
        lambda s: string_to_list(s) if isinstance(s, str) else s,
    )
    evaluation_df["predict"] = evaluation_df["predict"].apply(
        lambda s: string_to_list(s) if isinstance(s, str) else s,
    )
    return evaluation_df
