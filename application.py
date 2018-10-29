import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, credit_card

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Shows user's portfolio"""
    user_stocks = db.execute("SELECT * FROM portfolio WHERE id=:id", id=session["user_id"])

    stock_holdings = 0

    # Get current prices and update portfolio
    for stock in user_stocks:
        stock_symbol = stock["symbol"]
        stock_shares = stock["shares"]
        stock_info = lookup(stock_symbol)
        share_price = stock_info["price"]
        total_price = stock_shares * share_price
        stock_holdings += total_price
        db.execute("UPDATE portfolio SET price=:price, total=:total WHERE id=:id AND symbol=:symbol",
                   price=usd(share_price), total=usd(total_price), id=session["user_id"], symbol=stock_symbol)

    # Get user's available cash
    available_cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])

    # Add user's available cash to total holdings
    grand_total = available_cash[0]["cash"] + stock_holdings

    # If shares are equal to 0 then delete from portfolio
    db.execute("DELETE FROM portfolio WHERE id=:id and shares = 0", id=session["user_id"])

    # Get current portfolio
    current_portfolio = db.execute("SELECT * FROM portfolio WHERE id=:id ORDER BY symbol", id=session["user_id"])

    return render_template("index.html", stocks=current_portfolio, user_cash=usd(available_cash[0]["cash"]), grand_total=usd(grand_total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        shares_buying = int(request.form.get("shares"))

        # Look up stock information
        stock_info = lookup(request.form.get("symbol"))

        # Ensure symbol is valid
        if not stock_info:
            return apology("invalid symbol")

        # Variable for stock name
        symbol_buying = stock_info["symbol"]

        # Variable for stock price
        share_price = float(stock_info["price"])

        # Get user's cash
        available_cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])

        # Variable for the total purchase price
        purchase_price = share_price * shares_buying

        # Check if user can afford the shares
        if not available_cash or float(available_cash[0]["cash"]) < purchase_price:
            return apology("not enough cash available")

        # Update user's history
        db.execute("INSERT INTO history (id, symbol, transactions, price) \
                    VALUES (:id, :symbol, :transactions, :price)",
                   id=session["user_id"], symbol=symbol_buying,
                   transactions=shares_buying, price=share_price)

        # Check if user already owns shares from a company
        has_shares = db.execute("SELECT shares FROM portfolio WHERE id=:id AND symbol=:symbol",
                                id=session["user_id"], symbol=symbol_buying)

        # If user doesn't have shares from a company, insert into portfolio
        if not has_shares:
            db.execute("INSERT INTO portfolio (id, symbol, name, shares, price, total) \
                        VALUES (:id, :symbol, :name, :shares, :price, :total)",
                       id=session["user_id"], symbol=symbol_buying, name=stock_info["name"],
                       shares=shares_buying, price=share_price, total=purchase_price)
        # If user does have shares from the company, update portfolio
        else:
            db.execute("UPDATE portfolio SET shares=shares+:add_shares WHERE id=:id",
                       add_shares=shares_buying, id=session["user_id"])

        # Update user's available cash
        db.execute("UPDATE users SET cash=cash-:purchase WHERE id=:id", purchase=purchase_price, id=session["user_id"])

        # Redirect user to home page
        flash("Bought successfully!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Get user's history
    user_history = db.execute("SELECT * FROM history WHERE id=:id ORDER BY time", id=session["user_id"])

    return render_template("history.html", histories=user_history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username=:username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("Login successful!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Look up stock information
        stock_info = lookup(request.form.get("symbol"))

        # Ensure stock exists
        if not stock_info:
            return apology("invalid symbol")

        # Show user stock information
        return render_template("quoted.html", stock=stock_info, price=usd(stock_info["price"]))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Add registered user into database
        new_user = db.execute("INSERT INTO users (username, hash, keyword) VALUES (:username, :hash, :keyword)",
                              username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")),
                              keyword=request.form.get("keyword"))

        # Check the username is unique
        if not new_user:
            return apology("Username already exists")

        # Remember which user has logged in
        session["user_id"] = new_user

        # Redirect user to home page
        flash("Registered successfully!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    user_stocks = db.execute("SELECT * FROM portfolio WHERE id=:id", id=session["user_id"])

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Look up stock information
        stock_info = lookup(request.form.get("symbol"))

        # Variable for number of shares trying to sell
        shares_selling = int(request.form.get("shares"))

        # Get number of shares user owns
        user_shares = db.execute("SELECT shares FROM portfolio WHERE id=:id AND symbol=:symbol",
                                 id=session["user_id"], symbol=stock_info["symbol"])

        # Check if user has enough shares to sell
        if user_shares[0]["shares"] < shares_selling:
            return apology("you don't own enough shares")

        # Variable for price of the share
        share_price = float(stock_info["price"])

        # Variable for the total price of the sale
        sale_price = shares_selling * share_price

        # Update user's history to show a sell transaction
        db.execute("INSERT INTO history (id, symbol, transactions, price) \
                    VALUES (:id, :symbol, :transactions, :price)",
                   id=session["user_id"], symbol=stock_info["symbol"],
                   transactions=-shares_selling, price=share_price)

        # Update user's portfolio by deleting shares sold
        db.execute("UPDATE portfolio SET shares=shares-:shares_sold, total=total-:sale \
                    WHERE id=:id AND symbol=:symbol",
                   shares_sold=shares_selling, sale=sale_price,
                   id=session["user_id"], symbol=stock_info["symbol"])

        # Update user's available cash
        db.execute("UPDATE users SET cash=cash+:sale WHERE id=:id", sale=sale_price, id=session["user_id"])

        # Redirect user to home page
        flash("Sold successfully!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", stocks=user_stocks)


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Add more cash"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        new_money = request.form.get("new_money")
        cc_number = request.form.get("credit_number")

        # Ensure credit card number is valid
        credit_card(int(cc_number))
        if not cc_number or credit_card(int(cc_number)) == "INVALID":
            return apology("Invalid credit card number")

        # Add new money to user's available cash
        db.execute("UPDATE users SET cash=cash+:money WHERE id=:id", money=new_money, id=session["user_id"])

        # Redirect user to home page
        flash("Deposited money successfully with your " + credit_card(int(cc_number)) + " credit card!")
        return redirect("/")

    else:
        return render_template("deposit.html")


@app.route("/password-reset", methods=["GET", "POST"])
def passwordreset():
    """Allow users to reset password"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username and keyword
        rows = db.execute("SELECT * FROM users WHERE username=:user AND keyword=:keyword",
                          user=request.form.get("username"), keyword=request.form.get("keyword"))

        # Ensure username/keyword combination exists
        if len(rows) != 1:
            return apology("Username/Keyword combination invalid")

        # Update user's new password
        db.execute("UPDATE users SET hash=:newhash WHERE username=:user",
                   newhash=generate_password_hash(request.form.get("new_password")), user=request.form.get("username"))

        # Redirect user to home page
        return redirect("/password-reset-success")

    else:
        return render_template("password-reset.html")



@app.route("/password-reset-success")
def resetsuccess():
    return render_template("password-reset-success.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
