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
            return redirect("/login")
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
    """Checks if a credit card number is valid and returns the type of card"""

    if cc_number <= 0:
        return "INVALID"

    # Initialize variables
    numOfDigits = len(str(abs(cc_number)))
    sumDigits_mult2 = 0
    sumOfDigits = 0
    n = cc_number
    m = 0
    k = 0

    # Compute the sum according to algorithm
    while n != 0:
        sumOfDigits += n % 10
        n //= 10
        m = n % 10
        m *= 2
        if m >= 10:
            m = m % 10 + m // 10
            sumDigits_mult2 += m
        else:
            sumDigits_mult2 += m
        n //= 10
    sumOfDigits += sumDigits_mult2

    # Take first two digits of credit card number
    firstTwoDigits = cc_number
    for i in range((numOfDigits - 2)):
        firstTwoDigits //= 10

    # Check if credit card is valid and the type
    if sumOfDigits % 10 != 0:
        return "INVALID"
    else:
        if numOfDigits == 13:
            if (firstTwoDigits // 10) == 4:
                return "VISA"
            else:
                return "INVALID"
        elif numOfDigits == 15:
            if firstTwoDigits == 34 or firstTwoDigits == 37:
                return "AMEX"
            else:
                return "INVALID"
        elif numOfDigits == 16:
            if (firstTwoDigits // 10) == 4:
                return "VISA"
            elif firstTwoDigits >= 51 and firstTwoDigits <= 55:
                return "MASTERCARD"
            else:
                return "INVALID"
        else:
            return "INVALID"