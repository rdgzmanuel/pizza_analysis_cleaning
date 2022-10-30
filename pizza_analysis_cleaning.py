import pandas as pd
import datetime as dt
from typing import Dict
import numpy as np
import random
import re

def create_pizza_ingredients(df_pizza_types) -> Dict:
    """
    Generate a DataFrame containing each pizza as Keys and the
    ingredients as values (strings).
    """
    pizza_ingredients = {}
    for i in range(df_pizza_types.shape[0]):
        pizza_ingredients[df_pizza_types.loc[i, "pizza_type_id"]] = df_pizza_types.loc[i, "ingredients"]
    return pizza_ingredients

def create_ingredients(pizza_ingredients):
    """
    Create a dictionary with the amount of each ingredient we need.
    By default it starts as 0.
    """
    ingredients = {}
    for value in pizza_ingredients.values():
        particular_ingredients = value.split(", ")
        for ingredient in particular_ingredients:
            if ingredient not in ingredients:
                ingredients[ingredient] = 0
    return ingredients

def obtain_prices(df_pizzas):
    """
    DataFrame containing the price of each pizza
    """
    return  df_pizzas.groupby("pizza_type_id").sum()/3

def create_weekly_pizzas(df_orders, df_order_details, df_prices):
    """
    Create a new DataFrame representing the number of pizzas sold each
    week of 2015. This information helps us to compute the optimal number
    of pizzas we need to make to maximize the profits. We do this by computing
    the weekly average number of pizzas sold for each type. Then, we use the
    average profit margin of pizzas in USA, 15%, to calculate the optimal number
    of pizzas to make in order to lose as little money as possible.
    For each pizza type, we add the total money we would have lost each week
    if we had made a certain amount of pizzas. Then we pick the amount of
    pizzas with lhe least loses as optimal for each type. It is important to note
    that we have considered that the ingredients bought expire in a week, so there
    is no chnave they can be used the following week.
    """
    df_weekly_pizzas = pd.DataFrame()
    df_weekly_pizzas["pizza"] = pizza_ingredients.keys()
    df_weekly_pizzas["week 1"] = 0
    count = 0
    day = "01"
    i = 1
    j = 1
    # i represents the order id, j represnts the order details for each order id
    while i < df_orders.shape[0]:
        date = df_orders.loc[i, "date"]
        if date[:2] != day:
            count += 1
            day = date[:2]
            if count % 7 == 0:
                df_weekly_pizzas[f"week {int(count / 7) + 1}"] = 0
        while df_order_details.iloc[j, 1] == i and j < df_order_details.shape[0]:
            pizza = df_order_details.iloc[j, 2]
            quantity = int(df_order_details.iloc[j, 3])
            if pizza[-2] != "_":
                # We check this beacuse the greek pizza can be xl or xxl.
                pizza = pizza[:9]
            else:
                pizza = pizza[:-2]
            index = df_weekly_pizzas[df_weekly_pizzas["pizza"] == pizza].index
            df_weekly_pizzas.loc[index, f"week {int(count / 7) + 1}"] += quantity
            j += 1
        i += 1
    df_weekly_pizzas["mean"] = df_weekly_pizzas.iloc[:,1:52].sum(axis=1)/51
    # We add up to 51 weeks because the last one isn't complete
    df_weekly_pizzas["optimal"] = 0
    values = range(-8, 0)   # Deviations from the mean.
    for i in range(df_weekly_pizzas.shape[0]):
        profits = {}   
        # A dicitonary in which keys are possible deviations form the mean (-8 to +3) and values are profit for each deviation
        for value in values:
            profits[value] = 0
            mean = int(df_weekly_pizzas.loc[i, "mean"]) + value
            for j in range(1, 52):
                difference = mean - df_weekly_pizzas.iloc[i, j]
                if difference < 0:
                    profits[value] -= abs(difference)*df_prices.loc[df_weekly_pizzas.iloc[i, 0], "price"] * 0.15
                    # Supposing we have a 15% profit for each sold pizza
                elif difference > 0: 
                    profits[value] -= abs(difference)*df_prices.loc[df_weekly_pizzas.iloc[i, 0], "price"] * 0.85
                    # Because you spent a 85% of the final price but didn't sell it
        # Maximum profit and optimal deviations from the mean (will be updated in the second loop
        maximum = -100000   
        optimal = 0    
        for key, profit in profits.items():
            if maximum != max(maximum, profit):
                maximum, optimal = profit, key
        df_weekly_pizzas.loc[i, "optimal"] = int(mean) + optimal
        # Column in which we select the optimal number of pizzas to make in a week.
    return df_weekly_pizzas

def obtain_optimal(df_weekly_pizzas, pizza_ingredients, ingredients):
    """
    Iterate through the column optimal of df_weekly_pizzas to
    work out the aumount of each ingredient we need to be able to sell
    the number of pizzas previously calculated
    """
    for index, row in df_weekly_pizzas.iterrows():
        pizza = row["pizza"]
        quantity = int(row["optimal"])
        for ingredient in pizza_ingredients[pizza].split(", "):
            ingredients[ingredient] += quantity
    return ingredients

def show_strategy(optimal_ingredients):
    """
    Print our final results to see the quantity of each ingredient
    """
    spaces = 35
    print("Ingredients:" + " "*(spaces - len("Ingredients") - 1) + "Quantity:")
    print("-"*40)
    for key, value in optimal_ingredients.items():
        print(key + " "*(spaces - len(key)) + str(value))

def create_csv(optimal_ingredients):
    """
    Create a new dictionary to transform our data into 
    a DataFrame so it can be displayes as a csv
    """
    ingredients = {"Ingredients": [], "Quantity": []}
    for key, value in optimal_ingredients.items():
        ingredients["Ingredients"].append(key)
        ingredients["Quantity"].append(value)
    df = pd.DataFrame(ingredients)
    df.to_csv("optimal_ingredients.csv")

def recognize_format_date(str_date):
    """
    Returns the formats in which a date is introduced,
    0 if it is Nan or 1 is it is a string of numbers.
    """
    if type(str_date) == float:
        return "0"
    elif "." in str_date:
        return "1"
    else:
        if "-" in str_date:
            if ":" in str_date:
                return "%d-%m-%y %H:%M:%S"
            elif not str_date[0].isdigit():
                return "%a %d-%b-%Y"
            else:
                return "%Y-%m-%d"
        elif "," in str_date:
            return "%A,%d %B, %Y"
        else:
            return "%b %d %Y"

def clean_orders(df_orders):
    """
    Using the python module datetime to transform any time format
    into a standard easier to work with. In the first loop all the values are
    transformed except NaNs and strings of numbers, which are transformed afterwards.
    As we don't use the time of the order, tthat column is not modified.
    """
    for i in range(df_orders.shape[0]):
        date_format = recognize_format_date(df_orders.iloc[i, 1])
        if ":" in date_format:
            new_date = str(dt.datetime.strptime(df_orders.iloc[i, 1], date_format)).split()[0]
            date = new_date
            date = date[8:] + "/" + date[5:7] + "/" + date[:4]
            df_orders.iloc[i, 1] = date

        else:
            if date_format != "0" and date_format != "1":
                try:
                    new_date = str(dt.datetime.strptime(f"{df_orders.iloc[i, 1]}", f"{date_format}")).split()
                except:
                    df_orders.iloc[i, 1] = str(df_orders.iloc[i, 1])[:4] + "0" + str(df_orders.iloc[i, 1])[4:]
                    new_date = str(dt.datetime.strptime(f"{df_orders.iloc[i, 1]}", f"{date_format}")).split()
                
                date = new_date[0]
                # We can make a little modification to have the same
                # format as the previous dataset, so that the same functions
                # can be applied.
                date = date[8:] + "/" + date[5:7] + "/" + date[:4]
                df_orders.iloc[i, 1] = date
    
    for j in range(5):
        # We check five times to ensure there is no Nan left
        for i in range(df_orders.shape[0]):
            date_format = recognize_format_date(df_orders.iloc[i, 1])
            if date_format == "0":
                df_orders.iloc[i, 1] = df_orders.iloc[i - 1, 1]
                date_format = recognize_format_date(df_orders.iloc[i - 1, 1])
            elif date_format == "1":
                df_orders.iloc[i, 1] = df_orders.iloc[i + 1, 1]
                date_format = recognize_format_date(df_orders.iloc[i + 1, 1])
    
    return df_orders

def clean_order_details(pizza_ingredients, df_order_details):
    for i in range(df_order_details.shape[0]):
        pizza = df_order_details.iloc[i, 2]
        if type(pizza) != float:
            pizza = re.sub("[ -]", "_", pizza)
            pizza = re.sub("3", "e", pizza)
            pizza = re.sub("@", "a", pizza)
            pizza = re.sub("0", "o", pizza)
            df_order_details.iloc[i, 2] = pizza
        quantity = df_order_details.iloc[i, 3]
        if quantity in ["one", "One", "-1"] or type(quantity) == float:
            quantity = "1"
            df_order_details.iloc[i, 3] = quantity
        elif quantity in ["two", "Two", "-2"]:
            quantity = "2"
            df_order_details.iloc[i, 3] = quantity
    
    sizes = ["s", "m", "l"]
    pizzas = list(pizza_ingredients.keys())
    for i in range(df_order_details.shape[0]):
        if type(df_order_details.iloc[i, 2]) == float:
            df_order_details.iloc[i, 2] = pizzas[random.randint(0, len(pizzas) - 1)] + f"_{sizes[random.randint(0, 2)]}"
    return df_order_details



if __name__ == "__main__":
    df_order_details = pd.read_csv("order_details.csv", sep = ";", encoding="latin1")
    df_orders = pd.read_csv("orders.csv", sep=";")
    df_pizzas = pd.read_csv("pizzas.csv")
    df_pizza_types = pd.read_csv("pizza_types.csv", encoding="latin1")

    df_orders = df_orders.sort_values("order_id")
    df_orders = df_orders.reset_index(drop=True)
    df_orders.index = np.arange(1, len(df_orders) + 1)
    df_order_details = df_order_details.sort_values("order_details_id")
    df_order_details = df_order_details.reset_index(drop=True)
    df_order_details.index = np.arange(1, len(df_order_details) + 1)

    pizza_ingredients = create_pizza_ingredients(df_pizza_types)
    ingredients = create_ingredients(pizza_ingredients)

    df_prices = obtain_prices(df_pizzas)
    df_orders = clean_orders(df_orders)
    df_order_details = clean_order_details(pizza_ingredients, df_order_details)
    df_weekly_pizzas = create_weekly_pizzas(df_orders, df_order_details, df_prices)

    optimal_ingredients = obtain_optimal(df_weekly_pizzas, pizza_ingredients, ingredients)

    show_strategy(optimal_ingredients)
    create_csv(optimal_ingredients)