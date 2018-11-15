import math
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        response = requests.get(f"https://api.iextrading.com/1.0/stock/{urllib.parse.quote_plus(symbol)}/quote")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def credit_card(cc_number):
    """Checks if a credit card number is valid and returns the type of card
        Using the Luhn algorthm: https://www.geeksforgeeks.org/luhn-algorithm/"""

    # No negative numbers!
    if cc_number <= 0:
        return "INVALID"

    # Initialize variables
    number_digits = len(str(cc_number))
    sum_digits_multiplied_by_2 = 0
    total_sum = 0
    cc_number_copy = cc_number
    digit_multiplied_by_2 = 0

    # Compute the sum according to algorithm
    while cc_number_copy != 0:
        total_sum += cc_number_copy % 10
        cc_number_copy //= 10
        digit_multiplied_by_2 = cc_number_copy % 10
        digit_multiplied_by_2 *= 2
        if digit_multiplied_by_2 >= 10:
            # If the product after being multiplied by 2 is greater than 10, add the digits of the product
            digit_multiplied_by_2 = digit_multiplied_by_2 % 10 + digit_multiplied_by_2 // 10
            sum_digits_multiplied_by_2 += digit_multiplied_by_2
        else:
            sum_digits_multiplied_by_2 += digit_multiplied_by_2
        cc_number_copy //= 10
    total_sum += sum_digits_multiplied_by_2

    # Save first two digits of credit card number
    # Formula taken from https://stackoverflow.com/questions/41271299/how-can-i-get-the-first-two-digits-of-a-number
    first_two_digits = cc_number // 10 ** (int(math.log(cc_number, 10)) - 1)
    
    # Save first digit of credit card number
    first_digit = first_two_digits // 10

    # Check if credit card is valid and the type (Visa, Amex, or Mastercard)
    # Visa credit cards start with the number 4 and have a length of 13, 16, or 19
    # Amex credit cards start with 34 or 37 and have a length of 15
    # Mastercard credit cards start with a number between 51 and 55 inclusive and have a length of 16
    if total_sum % 10 != 0:
        return "INVALID"
    else:
        if number_digits == 13:
            if first_digit == 4:
                return "VISA"
            else:
                return "INVALID"
        elif number_digits == 15:
            if first_two_digits == 34 or first_two_digits == 37:
                return "AMEX"
            else:
                return "INVALID"
        elif number_digits == 16:
            if first_digit == 4:
                return "VISA"
            elif first_two_digits >= 51 and first_two_digits <= 55:
                return "MASTERCARD"
            else:
                return "INVALID"
        elif number_digits == 19:
            if first_digit == 4:
                return "VISA"
            else:
                return "INVALID"
        else:
            return "INVALID"