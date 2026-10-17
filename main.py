import json
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

STOCK_FILE = Path(__file__).parent / "stock.json"
#File locations
BASE_DIR = Path(__file__).resolve().parent

SALES_FILE = BASE_DIR / "sales.json"
STOCK_FILE = BASE_DIR / "stock.json"
MOVEMENTS_FILE = BASE_DIR / "movement.json"

#Commission rates and interest rate
LOWER_LIMIT = Decimal("100")
UPPER_LIMIT = Decimal("500")
LOW_RATE = Decimal("0.01")
HIGH_RATE = Decimal("0.05")
DAILY_INTEREST_RATE = Decimal("0.025")

def load_json(filename):
    """Load data from a JSON file."""
    with open(filename, "r",
encoding="utf-8") as file:
        return json.load(file)

def save_json(filename, data): 
    """Save data to a JSON file."""
    with open(filename, "w",
encoding="utf-8") as file: 
        json.dump(data, file, indent=4)

def money(value): 
    """Round a monetary value to two decimal places."""
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

# Sales commission

def calculate_commissions(sale):
    """Calculate commission for one transaction."""
    sale = Decimal(str(sale))

    if sale < LOWER_LIMIT:
        return Decimal("0.00")
    if sale <= UPPER_LIMIT:
        return money(sale * LOW_RATE)
    return money(sale * HIGH_RATE)


def calculate_sales_commissions():
    """Calculate total sales and commission for each seller."""

    try:
        sales_data = load_json(SALES_FILE)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Error reading sales.json: {error}")
        return

    if not isinstance(sales_data, dict):
        print("Error: Expected a JSON object containing sales.")
        return

    records = sales_data.get("sales")
    if not isinstance(records, list):
        print("Error: The sales record was not found.")
        return

    totals = {}

    for record in records:
        try:
            seller = record["seller"]
            sale = Decimal(str(record["value"]))

            if not isinstance(seller, str) or not seller.strip():
                raise ValueError("seller must be a non-empty string")
            if not sale.is_finite() or sale < 0:
                raise ValueError("sale value must be a finite, non-negative number")

        except (TypeError, KeyError, ValueError, ArithmeticError) as error:
            print(f"Skipping invalid sale: {error}")
            continue

        sale_commission = calculate_commissions(sale)

        if seller not in totals:
            totals[seller] = {
                "sales": Decimal("0.00"),
                "commission": Decimal("0.00"),
            }

        totals[seller]["sales"] += sale
        totals[seller]["commission"] += sale_commission

    if not totals:
        print("No valid sales records found.")
        return 
    
    return totals

# Display sales & total commission
sales_totals = calculate_sales_commissions()

if sales_totals:
    print("\n===== SALES COMMISSION =====")

    for seller, total in sales_totals.items():
        print(
            f"{seller}: Sales - R${total['sales']:.2f} "
            f"| Total Commission - R${total['commission']:.2f}"
        )

# STOCK MOVEMENTS
def stock_movements():
    """Record product entries and exits."""

    try:
        stock_data = load_json(STOCK_FILE)
    except FileNotFoundError:
        print("Error: stock.json was not found.")
        return
    except json.JSONDecodeError:
        print("Error: stock.json contains invalid JSON.")
        return

    if not isinstance(stock_data, dict):
        print("Error: invalid stock data.")
        return

    products = stock_data.get("stock")

    if not isinstance(products, list):
        print("Error: The stock array was not found.")
        return

    try:
        movements = load_json(MOVEMENTS_FILE)
    except FileNotFoundError:
        movements = []
    except json.JSONDecodeError:
        print("Error: movements.json contains invalid JSON.")
        return

    if not isinstance(movements, list):
        print("Error: invalid movement history.")
        return

    print("\n===== AVAILABLE PRODUCTS =====")

    for product in products:
        print(
            f"code: {product['productCode']} | "
            f"product: {product['productDescription']} | "
            f"Stock: {product['stock']}"
        )

    try:
        product_code = int(input("\nEnter product code: "))
    except ValueError:
        print("Invalid product code.")
        return

    product = next(
        (item for item in products if item["productCode"] == product_code),
        None,
    )

    if product is None:
        print("Product not found.")
        return

    movement_type = input("Enter movement type (entry/exit): ").strip().lower()
    if movement_type not in {"entry", "exit"}:
        print("Invalid movement type.")
        return

    try:
        quantity_text = input("Enter quantity: ").strip()
        quantity = int(quantity_text)
    except ValueError:
        print("Invalid quantity.")
        return

    if quantity <= 0:
        print("Quantity must be greater than zero.")
        return
    current_stock = product["stock"]

    if movement_type == "exit" and quantity > current_stock:
        print("Insufficient stock. Movement cancelled.")
        return

    if movement_type == "entry":
        new_stock = current_stock + quantity
        description = "Goods received into warehouse"
    else:
        new_stock = current_stock - quantity
        description = "Goods removed from warehouse"

#Create a unique movement ID
    movement_id = max((item["movementId"] for item in movements if isinstance(item, dict) 
                  and not isinstance(item.get("movementId"), bool)), default=0) + 1
    
    movement = {
        "movementId": movement_id,
        "description": description, 
        "type": movement_type, "productCode": product_code, 
        "productDescription": product["productDescription"],
        "quantity": quantity,
        "finalStock": new_stock,
        "date": date.today().isoformat()
    }

    # Save both files before confirming the movement
    original_stock = product["stock"]
    product["stock"] = new_stock

    try:
        save_json(STOCK_FILE, stock_data)
        movements.append(movement)
        save_json(MOVEMENTS_FILE, movements)
    except OSError as error:
        product["stock"] = original_stock 
        print(f"Could not save movement: {error}")
        return

    print("\n===== MOVEMENT RECORDED =====")
    print(f"Movement ID: {movement_id}")
    print(f"product: {product['productDescription']}")
    print(f"Description: {description}")
    print(f"Quantity moved: {quantity}")
    print(f"Final stock: {new_stock}")


# Get the amount owed
def calculate_interest():
    amount = float(input("Enter the amount owed: R$"))

    # Get the due date
    due_date_input = input("Enter the due date (YYYY-MM-DD): ")

    # Date
    due_date = datetime.strptime(
        due_date_input, "%Y-%m-%d"
    ).date()

    # Get today's date
    today = date.today()

    # Calculate overdue days
    days_overdue = max((today - due_date).days, 0)

    # Calculate interest
    daily_rate = 0.025
    interest = amount * daily_rate * days_overdue

    # Calculate the total amount due
    total_due = amount + interest

    # Display the results
    print("\n--- Interest Calculation ---")
    print(f"Original Amount: R${amount:.2f}")
    print(f"Due Date: {due_date}")
    print(f"Days Overdue: {days_overdue}")
    print(f"Interest: R${interest:.2f}")
    print(f"Total Amount Due: R${total_due:.2f}")

if __name__ == "__main__":
    # Record stock movements
    stock_movements()
    # Calculate interest
    calculate_interest()