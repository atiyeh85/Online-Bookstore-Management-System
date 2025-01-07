from flask import Flask, render_template, request,redirect, url_for,flash,session
import pymysql
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import mysql.connector
from flask import jsonify
from datetime import timedelta
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from functools import wraps
import json
import stripe
import traceback
stripe.api_key = "****"
app = Flask(__name__)
bcrypt = Bcrypt(app)
    
def get_db_connection():
    try:
        return pymysql.connect(
            host="localhost",
            user="root",
            password="*****",
            database="e_bookstore",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        print(f"Database connection error: {e}")
        return None


app.secret_key = 'IamatiyehAndIlOvemyfamily@'  # Required for flash messages
    

login_manager = LoginManager()
login_manager.init_app(app)
db = pymysql.connect(
        host="localhost",
        user="root",
        password="123456Sql!@#$%^",
        database="e_bookstore",
        charset="utf8mb4",
        
    )

# User class
class User(UserMixin):
    def __init__(self,  id, customer_id, username, email, roles=None):
        self.id = id
       
        self.username = username
        self.customer_id = customer_id
        self.email = email
        self.roles = roles or [] 


    def get_id(self):
        return str(self.id)
    
@login_manager.user_loader
def load_user(person_id):
    connection = get_db_connection()  # Create a new database connection
    if not connection:
        print("Failed to connect to the database.")
        return None

    cursor = connection.cursor()
    try:
        # Fetch user by person_id
        cursor.execute("""
            SELECT 
                p.person_id, 
                c.customer_id, 
                p.email, 
                p.username, 
                p.password, 
                GROUP_CONCAT(r.role_name) AS roles
            FROM person p
            LEFT JOIN customer c ON p.person_id = c.person_id
            LEFT JOIN person_role pr ON p.person_id = pr.person_id
            LEFT JOIN role r ON pr.role_id = r.role_id
            WHERE p.person_id = %s
            GROUP BY p.person_id, c.customer_id, p.email, p.username, p.password
        """, (person_id,))
        user_data = cursor.fetchone()

        if user_data:
            # Extract fields from the query result
            person_id = user_data['person_id']
            customer_id = user_data['customer_id']
            email = user_data['email']
            username = user_data['username']
            hashed_password = user_data['password']
            roles = user_data['roles']

            # Convert roles from comma-separated string to a list
            roles_list = roles.split(',') if roles else []

            # Return a User object with all the necessary attributes
            return User(id=person_id, customer_id=customer_id, username=username, email=email, roles=roles_list)
        else:
            print(f"No user found with person_id {person_id}")
            return None

    except Exception as e:
        print(f"Error loading user: {e}")
        return None

    finally:
        # Close the cursor and the connection
        cursor.close()
        connection.close()

bcrypt = Bcrypt()



def handle_message(message, success=True, status_code=200):
    """
    Handles messages for both JSON and non-JSON requests.
    
    Args:
        message (str): The message to display.
        success (bool): Whether the message indicates success or failure.
        status_code (int): The HTTP status code for JSON responses.

    Returns:
        Flask Response or None: JSON response for JSON requests; None for Flash messages.
    """
    if request.is_json:
        return jsonify({'success': success, 'message': message}), status_code
    else:
        flash(message, 'success' if success else 'danger')
        return None
@app.route('/data/popular_books')
@app.route('/data/popular_books')
def popular_books():
    cursor = db.cursor()
    query = """
    SELECT 
        book_title, 
        total_quantity_sold, 
        total_revenue_generated, 
        genre
    FROM 
        popular_books;
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    # Manually convert rows to a list of dictionaries
    books_data = []
    for row in rows:
        books_data.append({
            'book_title': row[0],
            'total_quantity_sold': row[1],
            'total_revenue_generated': row[2],
            'genre': row[3]
        })

    return jsonify(books_data)


@app.route('/addbook_Inventory', methods=['GET', 'POST'])
def addbook_Inventory():
    connection = get_db_connection()  # Establish a new database connection
    if not connection:
        return "Database connection failed", 500

    try:
        if request.method == 'POST':
            try:
                # Use the connection to create a cursor
                with connection.cursor() as cursor:
                    # Call the stored procedure
                    cursor.callproc('AddBookAndInventory', (
                        request.form['isbn'],
                        request.form['format_id'],
                        request.form['condition_id'],
                        request.form['price'],
                        request.form['available_quantity']
                    ))
                connection.commit()  # Commit the transaction
                flash("Book inventory added successfully!", "success")
                return redirect('/')
            except Exception as e:
                connection.rollback()  # Rollback in case of an error
                flash(f"Error adding book inventory: {str(e)}", "danger")
                return str(e), 500
        else:
            # Fetch format_id and condition_id data for dropdowns
            with connection.cursor() as cursor:
                cursor.execute("SELECT format_id, format_title FROM bookformat")
                formats = cursor.fetchall()

                cursor.execute("SELECT condition_id, condition_title FROM bookcondition")
                conditions = cursor.fetchall()

            return render_template('addbook_Inventory.html', formats=formats, conditions=conditions)
    finally:
        connection.close()  # Ensure the connection is closed
@app.route('/render_yearly_profit_data', methods=['GET'])
def render_yearly_profit_data():
    return render_template('render_yearly_profit_data.html')
@app.route('/data/yearly_profit_data')
def yearly_profit_data():
    cursor = db.cursor()  # Create the cursor without 'dictionary=True'
    query = """
    SELECT 
        order_year,
        total_revenue,
        total_cost,
        profit
    FROM 
        yearly_profit
    ORDER BY 
        order_year;
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    # Convert the rows to a dictionary manually
    data = []
    for row in rows:
        data.append({
            'order_year': row[0],
            'total_revenue': row[1],
            'total_cost': row[2],
            'profit': row[3]
        })

    return jsonify(data)


@app.route('/addbook', methods=['GET', 'POST'])
def addbook():
    if request.method == 'POST':
        try:
            cursor = db.cursor()

            # Collect form data
            isbn = request.form['isbn']
            title = request.form['title']
            genre_id = int(request.form['genre_id'])
            publisher_id = int(request.form['publisher_id'])
            image_path = f"{isbn}.png"  # Automatically set image path as ISBN.png
            
            

            # Collect selected authors as a comma-separated string
            selected_authors = request.form.getlist('authors')  # List of author IDs
            author_ids = ','.join(selected_authors)

            # Call the AddBookWithSelectedAuthors procedure
            cursor.callproc('AddBookWithSelectedAuthors', (
                isbn,
                title,
                genre_id,
                publisher_id,
                image_path,
                
              
                author_ids
            ))

            db.commit()
            flash('Book added successfully!')
            return redirect('/addbook')
        except Exception as e:
            db.rollback()  # Rollback on failure
            print(f"Error adding book: {e}")
            return f"An error occurred: {e}", 500
    else:
        try:
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # Fetch dropdown data for genres, publishers, and authors
            cursor.execute("SELECT genre_id, genre_title FROM genre")
            genres = cursor.fetchall()

            cursor.execute("SELECT publisher_id, publisher_name FROM publisher")
            publishers = cursor.fetchall()

            cursor.execute("SELECT author_id, author_name FROM author")
            authors = cursor.fetchall()
            # Fetch dropdown data for book formats and book conditions
            cursor.execute("SELECT format_id, format_title FROM bookformat")
            formats = cursor.fetchall()

            cursor.execute("SELECT condition_id, condition_title FROM bookcondition")
            conditions = cursor.fetchall()


            # Fetch list of books with authors
            cursor.execute("""
                
  SELECT 
    DISTINCT(b.isbn), 
    b.title AS book_title, 
    GROUP_CONCAT(a.author_name SEPARATOR ', ') AS authors,
    g.genre_title,
    p.publisher_name
FROM 
    book b
LEFT JOIN 
    book_author ba ON b.isbn = ba.isbn
LEFT JOIN 
    author a ON ba.author_id = a.author_id
LEFT JOIN 
    genre g ON b.genre_id = g.genre_id
LEFT JOIN 
    publisher p ON b.publisher_id = p.publisher_id
GROUP BY 
    b.isbn, 
    b.title, 
    g.genre_title, 
    p.publisher_name
ORDER BY 
    b.title;



            """)
            books_with_authors = cursor.fetchall()
            print(books_with_authors)

            return render_template(
                'addbook.html',
                genres=genres,
                formats=formats,
                conditions=conditions,
                publishers=publishers,
                authors=authors,
                books=books_with_authors
            )
       
        except Exception as e:
            print(f"Error fetching data: {e}")
            return f"An error occurred while fetching data: {e}", 500

@app.route('/manage_pricing_inventory', methods=['POST'])
def manage_pricing_inventory():
    pricing_id = request.form.get('pricing_id')
    isbn = request.form.get('isbn')
    format_id = request.form.get('format_id')
    condition_id = request.form.get('condition_id')
    price = float(request.form.get('price'))
    quantity = int(request.form.get('quantity'))
    available_quantity = int(request.form.get('available_quantity', 0))  # Default to 0 if not provided
    try:
        cursor = db.cursor()
        db.begin()

        # Ensure pricing_id exists in the book_pricing table
        if not pricing_id:
            flash("Invalid pricing ID.", "danger")
            return redirect(url_for('manage_books'))

        # Check if the row exists in book_inventory
        cursor.execute(
            "SELECT available_quantity, quantity FROM book_inventory WHERE pricing_id = %s",
            (pricing_id,)
        )
        inventory_row = cursor.fetchone()

        if inventory_row:
            # Row exists, update quantities
            new_available_quantity = inventory_row[0] + quantity
            new_quantity = inventory_row[1] + quantity
            cursor.execute(
                """
                UPDATE book_inventory
                SET available_quantity = %s,
                    quantity = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE pricing_id = %s
                """,
                (new_available_quantity, new_quantity, pricing_id)
            )
        else:
            # Row doesn't exist, calculate cost and insert
            cost = round(price * 0.7, 2)  # Calculate cost as price * 0.7 rounded to 2 decimals
            cursor.execute(
                """
                INSERT INTO book_inventory (pricing_id, available_quantity, quantity, cost)
                VALUES (%s, %s, %s, %s)
                """,
                (pricing_id, quantity, quantity, cost)
            )

        db.commit()
        flash('Pricing and inventory updated successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error updating pricing and inventory: {e}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('book_managing_detail', isbn=isbn))

@app.route('/get_available_quantity', methods=['GET'])
def get_available_quantity():
    isbn = request.args.get('isbn')
    format_id = request.args.get('format_id')
    condition_id = request.args.get('condition_id')
    print(format_id)
    print(format_id)
    try:
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT available_quantity 
            FROM book_inventory 
            JOIN book_pricing ON book_inventory.pricing_id = book_pricing.pricing_id
            WHERE book_pricing.isbn = %s 
              AND book_pricing.format_id = %s 
              AND book_pricing.condition_id = %s
            """,
            (isbn, format_id, condition_id)
        )
        print(result)
        result = cursor.fetchone()
        available_quantity = result['available_quantity'] if result else 0
        return {'available_quantity': available_quantity}, 200
    except Exception as e:
        return {'error': str(e)}, 500


def cleanup_expired_cart_items(customer_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Count items to be removed for the customer
            cursor.execute("""
                SELECT COUNT(*) AS expired_items 
                FROM cartitem
                WHERE customer_id = %s 
                  AND TIMESTAMPDIFF(HOUR, last_updated, NOW()) > 1;
            """, (customer_id,))
            expired_count = cursor.fetchone()['expired_items']

            if expired_count > 0:
                # Delete expired items
                cursor.execute("""
                    DELETE FROM cartitem
                    WHERE customer_id = %s 
                      AND TIMESTAMPDIFF(HOUR, last_updated, NOW()) > 1;
                """, (customer_id,))
                connection.commit()

                # Notify the user
                flash(f"{expired_count} items were removed from your cart due to inactivity.", "warning")
    finally:
        connection.close()



# ACID is Checked
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    # Ensure the user is authenticated
    if not current_user.is_authenticated:
        return jsonify({'status': 'error', 'message': 'You need to log in to add items to your cart.'}), 401

    data = request.get_json()
    pricing_id = data.get('pricing_id')
    quantity = data.get('quantity', 1)  # Default quantity is 1

    # Validate inputs
    if not pricing_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'Invalid item data or quantity'}), 400

    connection = get_db_connection()
    try:
        # Start a transaction
        connection.begin()

        with connection.cursor() as cursor:
            # Explicitly lock inventory row to check available_quantity
            cursor.execute("""
                SELECT available_quantity 
                FROM book_inventory 
                WHERE pricing_id = %s 
                FOR UPDATE
            """, (pricing_id,))
            inventory_result = cursor.fetchone()

            if not inventory_result:
                connection.rollback()
                return jsonify({'success': False, 'message': 'Item not found in inventory.'}), 404

            available_quantity = inventory_result['available_quantity']
            if available_quantity < quantity:
                connection.rollback()
                return jsonify({'success': False, 'message': 'Insufficient inventory to fulfill your request.'}), 400

            # Lock the cart item row for the current user and pricing_id
            cursor.execute("""
                SELECT quantity 
                FROM cartitem 
                WHERE customer_id = %s AND pricing_id = %s
                FOR UPDATE
            """, (current_user.customer_id, pricing_id))
            cart_result = cursor.fetchone()

            current_quantity_in_cart = cart_result['quantity'] if cart_result else 0

            # Enforce "maximum 4 items per cart item" rule
            if current_quantity_in_cart + quantity > 4:
                connection.rollback()
                return jsonify({
                    'success': False,
                    'message': f'You cannot purchase more than 4 units of this book in a single cart item. You currently have {current_quantity_in_cart} in your cart.'
                }), 400

            # Add or update the item in the cart
            if cart_result:
                # Update the existing row
                cursor.execute("""
                    UPDATE cartitem
                    SET quantity = quantity + %s
                    WHERE customer_id = %s AND pricing_id = %s
                """, (quantity, current_user.customer_id, pricing_id))
            else:
                # Insert a new row
                cursor.execute("""
                    INSERT INTO cartitem (customer_id, pricing_id, quantity)
                    VALUES (%s, %s, %s)
                """, (current_user.customer_id, pricing_id, quantity))

        # Commit the transaction
        connection.commit()
        return jsonify({'success': True, 'message': 'Item added to cart!'}), 200

    except Exception as e:
        connection.rollback()
        print("Error in add_to_cart:", str(e))
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        connection.close()

@app.route('/cart_count', methods=['GET'])
def cart_count():
    from flask_login import current_user

    # Ensure the user is authenticated
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'cart_count': 0}), 200

    connection = get_db_connection()
    try:
        # Start a transaction explicitly for read consistency
        connection.begin()

        with connection.cursor() as cursor:
            query = """
                SELECT SUM(quantity) AS total_items
                FROM cartitem
                WHERE customer_id = %s
            """
            # Execute the query
            cursor.execute(query, (current_user.customer_id,))
            result = cursor.fetchone()

            # If no items in the cart, default to 0
            total_items = result['total_items'] if result and result['total_items'] else 0

        # Commit the transaction for read stability (not strictly necessary for SELECT)
        connection.commit()

        return jsonify({'success': True, 'cart_count': total_items}), 200

    except Exception as e:
        # Rollback if there's an error (though no changes should be made here)
        connection.rollback()
        print("Error in cart_count:", str(e))
        return jsonify({'success': False, 'cart_count': 0, 'message': str(e)}), 500

    finally:
        connection.close()


@app.route('/cart', methods=['GET'])
def cart():
    # Ensure the user is authenticated
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    connection = get_db_connection()
    try:
        # Start a transaction explicitly for consistency
        connection.begin()

        with connection.cursor() as cursor:
            # Call the stored procedure to fetch cart items
            cursor.callproc('GetCartDetails', [current_user.customer_id])
            cart_items = cursor.fetchall()

            # Calculate the total cost of the cart
            total_cost = sum(item['total_price'] for item in cart_items)

        # Commit the transaction (not strictly necessary for a read, but ensures consistency)
        connection.commit()

        return render_template('cart.html', cart_items=cart_items, total_cost=total_cost)

    except Exception as e:
        # Rollback in case of any errors
        connection.rollback()
        print("Error fetching cart:", str(e))
        return render_template('cart.html', cart_items=[], total_cost=0, error=str(e))

    finally:
        #  close the connection
        connection.close()
@app.route('/update_cart_item', methods=['POST'])
def update_cart_item():
    # Ensure the user is authenticated
    if not current_user.is_authenticated:
        return handle_message("You need to log in to perform this action.", success=False, status_code=401) or redirect(url_for('login'))

    cart_item_id = request.form.get('cart_item_id')
    quantity = int(request.form.get('quantity'))
    MAX_QUANTITY = 4  # Define the maximum allowed quantity per item

    # Validate quantity
    if quantity <= 0:
        return handle_message("Quantity must be at least 1.", success=False, status_code=400) or redirect(url_for('cart'))

    if quantity > MAX_QUANTITY:
        return handle_message(f"Quantity cannot exceed {MAX_QUANTITY} per item.", success=False, status_code=400) or redirect(url_for('cart'))

    connection = get_db_connection()
    try:
        # Start a transaction
        connection.begin()

        with connection.cursor() as cursor:
            # Lock the cart item row with FOR UPDATE
            cursor.execute("""
                SELECT quantity
                FROM cartitem
                WHERE cart_item_id = %s AND customer_id = %s
                FOR UPDATE
            """, (cart_item_id, current_user.customer_id))
            cart_item = cursor.fetchone()

            if not cart_item:
                connection.rollback()
                return handle_message("Cart item not found.", success=False, status_code=404) or redirect(url_for('cart'))

            # Update the cart item quantity
            query = """
                UPDATE cartitem
                SET quantity = %s
                WHERE cart_item_id = %s AND customer_id = %s
            """
            cursor.execute(query, (quantity, cart_item_id, current_user.customer_id))

        # Commit the transaction
        connection.commit()

        return handle_message("Cart updated successfully.", success=True, status_code=200) or redirect(url_for('cart'))
    except Exception as e:
        # Rollback the transaction on failure
        connection.rollback()
        print("Error updating cart item:", str(e))
        return handle_message("Error updating cart item. Please try again.", success=False, status_code=500) or redirect(url_for('cart'))
    finally:
        # Close the connection
        connection.close()






@app.route('/remove_cart_item', methods=['POST'])
@login_required
def remove_cart_item():
    cart_item_id = request.form.get('cart_item_id')  # Retrieve the cart item ID from the form

    if not cart_item_id:
        flash("Invalid cart item.", "danger")
        return redirect(url_for('cart'))

    connection = get_db_connection()
    try:
        # Start a transaction
        connection.begin()

        with connection.cursor() as cursor:
            # Lock the cart item row with FOR UPDATE
            cursor.execute("""
                SELECT cart_item_id
                FROM cartitem
                WHERE cart_item_id = %s AND customer_id = %s
                FOR UPDATE
            """, (cart_item_id, current_user.customer_id))
            cart_item = cursor.fetchone()

            if not cart_item:
                connection.rollback()
                flash("Item not found in cart.", "danger")
                return redirect(url_for('cart'))

            # Remove the item from the cart
            cursor.execute("""
                DELETE FROM cartitem
                WHERE cart_item_id = %s AND customer_id = %s
            """, (cart_item_id, current_user.customer_id))

        # Commit the transaction
        connection.commit()
        flash("Item removed from your cart.", "success")
        return redirect(url_for('cart'))

    except Exception as e:
        # Rollback the transaction on failure
        connection.rollback()
        print("Error removing cart item:", str(e))
        flash("Error removing item. Please try again.", "danger")
        return redirect(url_for('cart'))

    finally:
        # Close the connection
        connection.close()

@app.route('/customer_orders')
@login_required
def customer_orders():
    customer_id = current_user.id  # Replace with your customer_id retrieval logic

    connection = get_db_connection()  # Ensure this method returns a valid DB connection
    try:
        # Start a transaction (optional for read consistency)
        connection.begin()

        # Query to fetch orders and join relevant tables
        query = """
        SELECT 
            o.order_id, 
            o.order_date, 
            o.total_amount, 
            COUNT(oi.or@app.route('/remove_cart_item', methods=['POST'])der_item_id) AS total_items, 
            os.status, 
            t.paymentmethod_id, 
            pm.paymentmethod_title 
        FROM `order` o
        LEFT JOIN orderitem oi ON o.order_id = oi.order_id
        LEFT JOIN order_status os ON o.order_status_id = os.order_status_id
        LEFT JOIN transaction t ON o.order_id = t.order_id
        LEFT JOIN paymentmethod pm ON t.paymentmethod_id = pm.paymentmethod_id
        WHERE o.customer_id = %s
        GROUP BY o.order_id
        ORDER BY o.order_date DESC
        """

        with connection.cursor() as cursor:
            cursor.execute(query, (customer_id,))
            orders = cursor.fetchall()

        # Commit the transaction (optional for read consistency)
        connection.commit()

        # Format data for template rendering
        formatted_orders = [
            {
                "order_id": row["order_id"],
                "order_date": row["order_date"],
                "total_amount": row["total_amount"],
                "total_items": row["total_items"],
                "status": row["status"],
                "payment_method": row["paymentmethod_title"],
            }
            for row in orders
        ]

        return render_template('orderconfirmation.html', orders=formatted_orders)

    except Exception as e:
        # Rollback in case of any errors
        connection.rollback()
        print("Error fetching customer orders:", str(e))
        return render_template('orderconfirmation.html', orders=[], error=str(e))

    finally:
        # Close the connection
        connection.close()

@app.route('/orderconfirmation/<int:transaction_id>')
@login_required
def orderconfirmation(transaction_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Use the view to fetch transaction and order details
            cursor.execute("""
                SELECT * 
                FROM vw_transaction_details
                WHERE transaction_id = %s AND customer_id = %s
            """, (transaction_id, current_user.customer_id))
            transaction = cursor.fetchone()

            if not transaction:
                flash("Transaction not found or access denied.", "danger")
                return redirect(url_for('customer_dashboard'))

            # Fetch order items
            cursor.execute("""
                SELECT 
                    oi.ordered_quantity AS quantity, 
                    oi.ordered_amount AS price, 
                    b.title
                FROM orderitem oi
                JOIN book_pricing bp ON oi.pricing_id = bp.pricing_id
                JOIN book b ON bp.isbn = b.isbn
                WHERE oi.order_id = %s
            """, (transaction['order_id'],))
            order_items = cursor.fetchall()

        return render_template(
            'orderconfirmation.html', 
            transaction=transaction, 
            order_items=order_items
        )

    except Exception as e:
        app.logger.error(f"Error fetching order confirmation: {e}")
        flash("An error occurred while fetching your order details. Please try again later.", "danger")
        return redirect(url_for('customer_dashboard'))
    finally:
        connection.close()

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    connection = get_db_connection()
    customer_id = session.get('customer_id')  # Use customer_id from session

    if not customer_id:
        flash("Customer not found. Please log in again.", "danger")
        return redirect(url_for('login'))

    try:
        if request.method == 'POST':
            # Start a transaction
            connection.begin()

            # Fetch form data
            address_id = request.form.get('address_id')
            paymentmethod_id = request.form.get('paymentmethod_id')

            # Check if a new address is provided
            new_address = {
                'address_line1': request.form.get('address_line1'),
                'address_line2': request.form.get('address_line2'),
                'city_id': request.form.get('city_id'),
                'state_id': request.form.get('state_id'),
                'postalcode': request.form.get('postalcode'),
            }

            # Validate new address input
            if not address_id and not new_address['address_line1']:
                flash("Please select or provide a shipping address.", "danger")
                return redirect(url_for('checkout'))

            with connection.cursor() as cursor:
                # Fetch person_id for the current customer
                cursor.execute("""
                    SELECT person_id FROM customer WHERE customer_id = %s
                """, (customer_id,))
                person = cursor.fetchone()

                if not person:
                    flash("Unable to find customer information.", "danger")
                    return redirect(url_for('checkout'))

                person_id = person['person_id']

                # Save the new address if provided
                if new_address['address_line1']:
                    if not new_address['city_id'] or not new_address['state_id'] or not new_address['postalcode']:
                        flash("All address fields are required.", "danger")
                        return redirect(url_for('checkout'))

                    # Deactivate all other addresses for this customer
                    cursor.execute("""
                        UPDATE address
                        SET status = 0
                        WHERE person_id = %s
                    """, (person_id,))

                    # Insert the new address with status = true (active)
                    cursor.execute("""
                        INSERT INTO address (status, type, person_id, address_line1, address_line2, city_id, state_id, postalcode)
                        VALUES (1, 'shipping', %s, %s, %s, %s, %s, %s)
                    """, (
                        person_id,
                        new_address['address_line1'],
                        new_address['address_line2'],
                        new_address['city_id'],
                        new_address['state_id'],
                        new_address['postalcode']
                    ))
                    address_id = cursor.lastrowid  # Use the newly created address ID

                # Fetch cart items with updated prices and lock inventory rows
                cursor.execute("""
                    SELECT c.pricing_id, c.quantity, bp.price, bi.available_quantity
                    FROM cartitem c
                    JOIN book_pricing bp ON c.pricing_id = bp.pricing_id
                    JOIN book_inventory bi ON c.pricing_id = bi.pricing_id
                    WHERE c.customer_id = %s FOR UPDATE
                """, (customer_id,))
                cart_items = cursor.fetchall()

                if not cart_items:
                    flash("Your cart is empty. Please add items to your cart.", "danger")
                    return redirect(url_for('checkout'))

                # Validate inventory availability
                for item in cart_items:
                    if item['quantity'] > item['available_quantity']:
                        flash(f"Insufficient stock for item with pricing_id {item['pricing_id']}.", "danger")
                        return redirect(url_for('checkout'))

                # Calculate total amount
                total_amount = sum(item['quantity'] * item['price'] for item in cart_items)

                # Insert the order
                cursor.execute("""
                    INSERT INTO `order` (customer_id, order_date, total_amount, order_status_id)
                    VALUES (%s, NOW(), %s, 1)  -- Status 1: Pending
                """, (customer_id, total_amount))
                order_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO order_status_history (order_id, order_status_id, change_date)
                    VALUES (%s, 1, NOW())
                """, (order_id,))
                 
                # Insert items into the orderitem table and update inventory
                for item in cart_items:
                    ordered_quantity = item['quantity']
                    ordered_amount = item['quantity'] * item['price']
                    cursor.execute("""
                        INSERT INTO orderitem (order_id, pricing_id, ordered_quantity, ordered_amount)
                        VALUES (%s, %s, %s, %s)
                    """, (order_id, item['pricing_id'], ordered_quantity, ordered_amount))

                    # Deduct inventory
                    cursor.execute("""
                        UPDATE book_inventory
                        SET available_quantity = available_quantity - %s
                        WHERE pricing_id = %s
                    """, (ordered_quantity, item['pricing_id']))

                # Insert transaction record
                cursor.execute("""
                    INSERT INTO transaction (order_id, paymentmethod_id, transaction_totalamount, transactiont_date)
                    VALUES (%s, %s, %s, NOW())
                """, (order_id, paymentmethod_id, total_amount))
                transaction_id = cursor.lastrowid

                # Clear the cart
                cursor.execute("DELETE FROM cartitem WHERE customer_id = %s", (customer_id,))

            # Commit the transaction
            connection.commit()

            flash("Order placed successfully!", "success")
            return redirect(url_for('orderconfirmation', transaction_id=transaction_id))

        with connection.cursor() as cursor:
            # Fetch cart items with updated prices
            cursor.execute("""
                SELECT c.cart_item_id, c.pricing_id, b.title, c.quantity, bp.price AS unitprice, 
                       (c.quantity * bp.price) AS total_price
                FROM cartitem c
                JOIN book_pricing bp ON c.pricing_id = bp.pricing_id
                JOIN book b ON bp.isbn = b.isbn
                WHERE c.customer_id = %s
            """, (customer_id,))
            cart_items = cursor.fetchall()

            if not cart_items:
                flash("Your cart is empty. Please add items to your cart.", "info")
                return redirect(url_for('allbooks'))

            # Calculate total amount
            total_amount = sum(item['total_price'] for item in cart_items)

            # Fetch only active address
            cursor.execute("""
                SELECT address_id, address_line1, address_line2, city_id, state_id, postalcode
                FROM address
                WHERE person_id = (SELECT person_id FROM customer WHERE customer_id = %s)
                AND status = 1
            """, (customer_id,))
            addresses = cursor.fetchall()

            # Fetch available payment methods
            cursor.execute("SELECT paymentmethod_id, paymentmethod_title FROM paymentmethod")
            paymentmethods = cursor.fetchall()

            # Fetch available cities and states
            cursor.execute("SELECT city_id, city_name FROM city")
            cities = cursor.fetchall()

            cursor.execute("SELECT state_id, state_name FROM state")
            states = cursor.fetchall()

        return render_template(
            'checkout.html',
            cart_items=cart_items,
            total_amount=total_amount,
            addresses=addresses,
            paymentmethods=paymentmethods,
            cities=cities,
            states=states
        )

    except Exception as e:
        # Rollback the transaction on error
        connection.rollback()
        app.logger.error(f"Error during checkout and order placement: {e}")
        flash("An error occurred during checkout. Please try again.", "danger")
        return redirect(url_for('allbooks'))
    finally:
        # Close the connection
        connection.close()

@app.context_processor
def inject_popular_books():
    """Fetch the most popular books of 2024."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Query to fetch most popular books in 2024
            cursor.execute("""
                SELECT b.title, SUM(oi.ordered_quantity) AS total_sold
                FROM orderitem oi
                JOIN book_pricing bp ON oi.pricing_id = bp.pricing_id
                JOIN book b ON bp.isbn = b.isbn
                JOIN `order` o ON oi.order_id = o.order_id
                WHERE YEAR(o.order_date) = 2024
                GROUP BY b.title
                ORDER BY total_sold DESC
                LIMIT 5
            """)
            popular_books = cursor.fetchall()
    finally:
        connection.close()

    # Return the popular books to be available in all templates
    return {'popular_books': popular_books}        
@app.route('/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    # Ensure only employees can update statuses
    if 'employee' not in current_user.roles:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('employee_dashboard'))

    # Parse the form data
    order_id = request.form.get('order_id')
    new_status_id = request.form.get(f'order_status_id_{order_id}')
  
    if not order_id or not new_status_id:
        flash("Invalid input.", "danger")
        return redirect(url_for('employee_dashboard'))

    connection = get_db_connection()
    try:
        # Start a transaction
        connection.begin()
        with connection.cursor() as cursor:
            # Validate the new status ID
            
            # Update the order status in the `order` table
            cursor.execute("""
                UPDATE `order`
                SET order_status_id = %s
                WHERE order_id = %s
            """, (new_status_id, order_id))
            # Insert a record into the `order_status_history` table
            print(current_user.id)

            cursor.execute("""
                INSERT INTO order_status_history (order_id, order_status_id, change_date, updated_by)
                VALUES (%s, %s, NOW(), %s)
            """, (order_id, new_status_id, current_user.id))

        # Commit the transaction
        connection.commit()
        flash("Order status updated successfully.", "success")
    except Exception as e:
        # Rollback the transaction on error
        connection.rollback()
        app.logger.error(f"Error updating order status: {e}")
        flash("An error occurred while updating the order status.", "danger")
    finally:
        # Ensure the database connection is closed
        connection.close()

    return redirect(url_for('employee_dashboard'))

@app.route('/orders', methods=['GET'])
def orders():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    customer_id = current_user.id

    try:
        cursor = db.cursor()
        cursor.execute("""
            SELECT o.order_id, o.order_date, o.total_amount, os.status 
            FROM `order` o
            JOIN orderstatus os ON o.order_status_id = os.order_status_id
            WHERE o.customer_id = %s
        """, (customer_id,))
        orders = cursor.fetchall()
    except Exception as e:
        orders = []
        flash(f'Error: {e}', 'danger')
    finally:
        cursor.close()
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Capture input fields and user information
        username = request.form.get('username')
        password = request.form.get('password')
        ip_address = request.remote_addr  # Get the user's IP address
        login_source = 'web'  # Define the login source (e.g., 'web', 'mobile', etc.)

        # Validate fields before proceeding
        if not username or not password:
            flash('Both username and password are required!', 'danger')
            return render_template('login.html')

        try:
            # Start a database transaction by initializing a cursor
            cursor = db.cursor()

            # Step 1: Query user credentials and customer_id
            cursor.execute("""
                SELECT p.person_id, p.username, p.email, p.password, c.customer_id
                FROM person p
                LEFT JOIN customer c ON p.person_id = c.person_id
                WHERE p.username = %s
            """, (username,))
            person = cursor.fetchone()
            print(person)
            if person:
                # Destructure the fetched user information
                person_id, db_username, email, hashed_password, customer_id = person

                # Ensure hashed_password exists (to avoid invalid users)
                if not hashed_password:
                    flash('Invalid user credentials.', 'danger')
                    return render_template('login.html')

                # Step 2: Check the provided password against the hashed password
                if bcrypt.check_password_hash(hashed_password, password):
                    # Password is valid, fetch user roles
                    cursor.execute("""
                        SELECT r.role_name 
                        FROM role r
                        INNER JOIN person_role ur ON r.role_id = ur.role_id
                        WHERE ur.person_id = %s
                    """, (person_id,))
                    roles = [role[0] for role in cursor.fetchall()]  # Fetch all roles as a list

                    if not roles:
                        # No roles assigned to the user, log an error and exit
                        flash('No roles assigned to this user!', 'danger')
                        return render_template('login.html')

                    # Step 3: Log successful login into `login_audit` table
                    cursor.execute("""
                        INSERT INTO login_audit (person_id, attempt_time, ip_address, success, failure_reason, login_source)
                        VALUES (%s, NOW(), %s, %s, %s, %s)
                    """, (person_id, ip_address, 1, None, login_source))

                    # Step 4: Commit transaction to finalize changes in the database
                    db.commit()

                    # Create a User object and log in the user
                    user = User(id=person_id, customer_id=customer_id, email=email, username=db_username, roles=roles)
                    login_user(user)
                    session['customer_id'] = customer_id  # Save customer ID in session
                    flash('Login successful!', 'success')

                    # Step 5: Redirect logic based on user roles
                    if 'employee' in roles and 'customer' in roles:
                        return redirect(url_for('employee_dashboard'))  # Unified dashboard
                    elif 'employee' in roles:
                        return redirect(url_for('employee_dashboard'))
                    elif 'customer' in roles:
                        return redirect(url_for('allbooks'))
                    else:
                        flash('No appropriate dashboard found for your roles.', 'danger')
                        return redirect(url_for('login'))
                else:
                    # Step 3 (Failed Login): Log failed login into `login_audit` table
                    cursor.execute("""
                        INSERT INTO login_audit (person_id, attempt_time, ip_address, success, failure_reason, login_source)
                        VALUES (%s, NOW(), %s, %s, %s, %s)
                    """, (person_id, ip_address, 0, 'Incorrect password', login_source))

                    # Commit transaction for the failed login attempt
                    db.commit()

                    # Inform the user about incorrect credentials
                    flash('Invalid username or password.', 'danger')
            else:
                # Step 3 (Failed Login for unknown user): Log the failed attempt with no user ID
                cursor.execute("""
                    INSERT INTO login_audit (person_id, attempt_time, ip_address, success, failure_reason, login_source)
                    VALUES (%s, NOW(), %s, %s, %s, %s)
                """, (None, ip_address, 0, 'User not found', login_source))

                # Commit the transaction for this failed login attempt
                db.commit()

                # Inform the user that the username is invalid
                flash('Invalid username or password.', 'danger')

        except Exception as e:
            # Step 6: Rollback transaction in case of any errors
            db.rollback()  # Undo any changes made during the transaction
            flash(f'Error during login: {e}', 'danger')

        finally:
            # Ensure the cursor is always closed after processing
            cursor.close()

    # Render the login page if the method is GET or no valid submission
    return render_template('login.html')



def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            
            if not current_user.is_authenticated or required_role not in current_user.roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/employee_dashboard', methods=['GET'])
@login_required
def employee_dashboard():
    # Fetch filter inputs from the request
    customer_name = request.args.get('customer_name', '').strip()
    order_status_id = request.args.get('status', '').strip()
    order_date_from = request.args.get('order_date_from', '')
    order_date_to = request.args.get('order_date_to', '')
    order_id = request.args.get('order_id', '').strip()
    customer_email = request.args.get('customer_email', '').strip()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Build the query dynamically based on filters
            query = """
                SELECT 
                    order_id,
                    customer_name,
                    customer_email,
                    order_status_id,
                    order_status,
                    order_total,
                    order_date,
                    book_format,
                    book_condition,
                    book_title,
                    ordered_quantity,
                    line_total,
                    image_path
                    
                FROM order_report_view
                WHERE 1=1
            """
            params = []

            if order_id:
                query += " AND order_id = %s"
                params.append(order_id)
            if customer_name:
                query += " AND customer_name LIKE %s"
                params.append(f"%{customer_name}%")
            if customer_email:
                query += " AND customer_email LIKE %s"
                params.append(f"%{customer_email}%")
            if order_status_id:
                query += " AND order_status_id = %s"
                print(query)

                params.append(order_status_id)
            if order_date_from:
                query += " AND order_date >= %s"
                params.append(order_date_from)
            if order_date_to:
                query += " AND order_date <= %s"
                params.append(order_date_to)
            # Execute the query
            cursor.execute(query, params)
            orders = cursor.fetchall()
            print(current_user.roles)
            # Fetch all order statuses for the dropdown
            cursor.execute("""
                SELECT order_status_id, status AS status_name
                FROM order_status
            """)
            order_statuses = cursor.fetchall()

        # Pass both orders and order statuses to the template
        return render_template(
            'employee_dashboard.html', 
            orders=orders, 
            order_statuses=order_statuses,
            filters={
                'order_id': order_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'status': order_status_id,
                'order_date_from': order_date_from,
                'order_date_to': order_date_to
            }
        )
    except Exception as e:
        app.logger.error(f"Error fetching order report: {e}")
        flash("An error occurred while fetching the order report. Please try again.", "danger")
        return redirect(url_for('employee_dashboard'))
    finally:
        connection.close()

@app.route('/charts')
def charts():
    connection = get_db_connection()  # Ensure this function establishes a valid DB connection
    try:
        with connection.cursor() as cursor:
            # Fetch data for `sales_by_book_month_year`
            cursor.execute("SELECT book_title, sale_year, sale_month, total_quantity_sold FROM sales_by_book_month_year")
            book_sales_month = cursor.fetchall()

            # Fetch data for `sales_by_book_year`
            cursor.execute("SELECT book_title, sale_year, total_quantity_sold FROM sales_by_book_year")
            book_sales_year = cursor.fetchall()

            # Fetch data for `sales_by_genre_month_year`
            cursor.execute("SELECT genre_name, sale_year, sale_month, total_quantity_sold FROM sales_by_genre_month_year")
            genre_sales_month = cursor.fetchall()

            # Fetch data for `sales_by_genre_year`
            cursor.execute("SELECT genre_name, sale_year, total_quantity_sold FROM sales_by_genre_year")
            genre_sales_year = cursor.fetchall()

            # Fetch data for `sales_by_age_range`
            cursor.execute("SELECT age_range, total_orders,total_quantity_sold AS sales FROM sales_by_age_range")
            sales_by_age_range = cursor.fetchall()
            print(sales_by_age_range)
        # Pass the data to the template
        return render_template(
            'charts.html',
            book_sales_month=book_sales_month,
            book_sales_year=book_sales_year,
            genre_sales_month=genre_sales_month,
            genre_sales_year=genre_sales_year,
            sales_by_age_range=sales_by_age_range  # Added this line
        )
    finally:
        connection.close()
@app.route('/compare_years_months', methods=['GET'])
def compare_years_months():
    # Render the template for the chart
    return render_template('compare_years_months.html')


@app.route('/data/compare_years_months', methods=['GET'])
def compare_years_months_data():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Query to fetch sales data grouped by year and month
            cursor.execute("""
                SELECT 
                    sale_year AS year, 
                    sale_month AS month, 
                    SUM(total_quantity_sold) AS total_sold
                FROM sales_by_book_month_year
                GROUP BY year, month
                ORDER BY year, month
            """)
            sales_data = cursor.fetchall()

        # Prepare data for Chart.js
        labels = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        datasets = {}

        for row in sales_data:
            year = row['year']
            month = row['month'] - 1  # Adjust for zero-based indexing in Chart.js
            total_sold = row['total_sold']

            if year not in datasets:
                datasets[year] = [0] * 12
            datasets[year][month] = total_sold

        # Format data for Chart.js
        chart_data = {
            "labels": labels,
            "datasets": [
                {
                    "label": str(year),
                    "data": datasets[year],
                    "fill": False,
                    "borderColor": f"rgba({255 - i * 40}, 99, {132 + i * 40}, 1)",
                    "backgroundColor": f"rgba({255 - i * 40}, 99, {132 + i * 40}, 0.5)",
                    "tension": 0.1
                }
                for i, year in enumerate(sorted(datasets.keys()))
            ]
        }

        # Return JSON data
        return jsonify(chart_data)

    finally:
        connection.close()

@app.route('/customer_dashboard')
def customer_dashboard():
    customer_id = session.get('customer_id')  # Assuming customer_id is stored in the session
    period = request.args.get('period', 'all')  # Get period from query parameters (default to 'all')
    connection = get_db_connection()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Fetch orders for the customer
        query = """
    SELECT 
        * 
    FROM 
        latest_order_status 
    WHERE 
        customer_id = %s
"""

         
        params = [customer_id]

        # Add date filtering based on the selected period
        if period == 'last_6_months':
            query += " AND o.order_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)"
        elif period == 'last_1_year':
            query += " AND o.order_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)"

        query += " ORDER BY o.order_date DESC"
        cursor.execute(query, params)
        orders = cursor.fetchall()

        # Fetch order items
        cursor.execute("""
           SELECT 
    oi.order_id, 
    b.title AS book_title, 
    b.image_path,
    GROUP_CONCAT(DISTINCT a.author_name SEPARATOR ', ') AS authors, 
    oi.ordered_quantity, 
    oi.ordered_amount AS line_total, 
    bf.format_title,
    bc.condition_title
FROM `orderitem` oi
JOIN `book_pricing` bp ON oi.pricing_id = bp.pricing_id
JOIN `bookformat` bf ON bf.format_id = bp.format_id
JOIN `bookcondition` bc ON bc.condition_id = bp.condition_id
JOIN `book` b ON bp.isbn = b.isbn
LEFT JOIN `book_author` ba ON b.isbn = ba.isbn
LEFT JOIN `author` a ON ba.author_id = a.author_id
GROUP BY 
    oi.order_id, 
    b.title, 
    b.image_path, 
    oi.ordered_quantity, 
    oi.ordered_amount, 
    bf.format_title,
    bc.condition_title;

        """)
        order_items = cursor.fetchall()

    # Organize order items by order_id
    order_items_map = {}
    for item in order_items:
        if item['order_id'] not in order_items_map:
            order_items_map[item['order_id']] = []
        order_items_map[item['order_id']].append(item)
        # Fetch order statuses
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT order_status_id, status FROM order_status")
            order_statuses = cursor.fetchall()
    return render_template(
        'customer_dashboard.html',
        orders=orders,
        order_items_map=order_items_map,
        selected_period=period,
        order_statuses=order_statuses
    )

def roles_required(*required_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not any(role in current_user.roles for role in required_roles):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/dashboard')
@roles_required('customer', 'employee')  # Allow both 'customer' and 'employee'
def dashboard():
    return render_template('dashboard.html')    



@app.route('/autocomplete/authors', methods=['GET'])
def autocomplete_authors():
    search_query = request.args.get('q', '').strip()
    if not search_query:
        return jsonify([])  # Return an empty list if no query is provided

    # Simulated database query for author names
    cursor = db.cursor()
    cursor.execute("SELECT DISTINCT author_name FROM allbooks WHERE author_name LIKE %s LIMIT 10", [f"%{search_query}%"])
    authors = [row[0] for row in cursor.fetchall()]
    cursor.close()

    # Return the list of authors as JSON
    return jsonify(authors)
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Collect form data
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = 'customer'  # Default role is 'customer'

        # Debugging statements
        print(f"Password: {password}, Confirm Password: {confirm_password}")

        # Validate required fields (you can add checks for fname, lname, email, etc.)
        if not password or not confirm_password:
            flash('Password and confirm password are required!', 'danger')
            return render_template('register.html', fname=fname, lname=lname, username=username, email=email)

        # Validate password confirmation
        if password.strip() != confirm_password.strip():  # Strip any whitespace
            flash('Passwords do not match!', 'danger')
            return render_template('register.html', fname=fname, lname=lname, username=username, email=email)

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        try:
            cursor = db.cursor()
            # Call the stored procedure to register the user
            cursor.callproc(
                'RegisterUser',
                (fname, lname, email, username, hashed_password, role)
            )
            db.commit()

            flash('Registration successful!', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.rollback()
            flash(f"Error during registration: {str(e)}", "danger")
            return render_template('register.html', fname=fname, lname=lname, username=username, email=email)

        finally:
            cursor.close()

    return render_template('register.html')


             

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('allbooks'))  

@app.route('/render_customer_login_summary', methods=['GET'])

@app.route('/render_customer_login_summary', methods=['GET'])
def render_customer_login_summary():
    return render_template('render_customer_login_summary.html')

       
@app.route('/data/customer_login_summary', methods=['GET'])
def get_customer_login_summary():
    try:
        # Query the database for the top 10 customers in 2024
        cursor = db.cursor()
        query = """
            SELECT 
                customer_id, 
                full_name, 
                total_attempts, 
                total_successful_attempts, 
                total_failed_attempts
            FROM 
                customer_login_summary
            WHERE 
                login_year = 2024
            ORDER BY 
                total_attempts DESC
            LIMIT 10;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()

        # Format results as JSON
        data = []
        for row in results:
            data.append({
                "customer_id": row[0],
                "full_name": row[1],
                "total_attempts": row[2],
                "total_successful_attempts": row[3],
                "total_failed_attempts": row[4],
            })

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})
    
@app.route('/render_users_by_year', methods=['GET'])
def render_users_by_year():
    return render_template('render_users_by_year.html')

@app.route('/data/users_by_year', methods=['GET'])
def get_users_by_year():
    role = request.args.get('role', 'customer')
    
    # Validate role
    if role not in ['customer', 'employee', 'both']:
        return jsonify({'error': 'Invalid role specified'}), 400

    try:
        # Query templates
        if role == 'both':
            query = """
                SELECT 
                    YEAR(p.created_at) AS registration_year,
                    COUNT(DISTINCT p.person_id) AS total_users
                FROM 
                    person p
                JOIN 
                    person_role pr ON p.person_id = pr.person_id
                JOIN 
                    role r ON pr.role_id = r.role_id
                WHERE 
                    p.status = true
                    AND r.role_name IN ('customer', 'employee')
                GROUP BY 
                    YEAR(p.created_at)
                ORDER BY 
                    registration_year ASC;
            """
            params = None
        else:
            query = """
                SELECT 
                    YEAR(p.created_at) AS registration_year,
                    COUNT(DISTINCT p.person_id) AS total_users
                FROM 
                    person p
                JOIN 
                    person_role pr ON p.person_id = pr.person_id
                JOIN 
                    role r ON pr.role_id = r.role_id
                WHERE 
                    p.status = true
                    AND r.role_name = %s
                GROUP BY 
                    YEAR(p.created_at)
                ORDER BY 
                    registration_year ASC;
            """
            params = (role,)

        # Execute query
        with db.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()

        # Prepare data for Chart.js
        data = {'years': [row[0] for row in results], 'counts': [row[1] for row in results]}
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/render_users_by_month', methods=['GET'])
def render_users_by_month():
    return render_template('render_users_by_month.html')



@app.route('/data/total_users', methods=['GET'])
def total_users():
    try:
        # Connect to the database and execute query
        cursor = db.cursor()
        query = """
            SELECT 
                r.role_name, 
                COUNT(DISTINCT p.person_id) AS total_users
            FROM 
                person p
            JOIN 
                person_role pr ON p.person_id = pr.person_id
            JOIN 
                role r ON pr.role_id = r.role_id
            WHERE 
                p.status = true
            GROUP BY 
                r.role_name;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()

        # Prepare response as a dictionary
        data = {row[0]: row[1] for row in results}

        return jsonify(data)  # Return JSON response
    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/data/users_by_month', methods=['GET'])
def get_users_by_month():
    role = request.args.get('role', 'customer')  # Default role is 'customer'
    try:
        cursor = db.cursor()
        query = """
            SELECT 
                YEAR(p.created_at) AS registration_year,
                MONTH(p.created_at) AS registration_month,
                COUNT(DISTINCT p.person_id) AS total_users
            FROM 
                person p
            JOIN 
                person_role pr ON p.person_id = pr.person_id
            JOIN 
                role r ON pr.role_id = r.role_id
            WHERE 
                p.status = true AND r.role_name = %s
            GROUP BY 
                registration_year, registration_month
            ORDER BY 
                registration_year, registration_month;
        """
        cursor.execute(query, (role,))
        results = cursor.fetchall()
        cursor.close()

        # Prepare data for JSON response
        data = {}
        for row in results:
            year = row[0]
            month = row[1]
            count = row[2]

            # Organize data by year
            if year not in data:
                data[year] = [0] * 12  # Initialize an array for 12 months
            data[year][month - 1] = count  # Populate the month's index (0-based)

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})


  


@app.route('/add_author', methods=['GET', 'POST'])
@roles_required('employee') 
def add_author():
    if request.method == 'POST':
        # Retrieve form data
        author_name = request.form.get('author_name') 
        author_disctiption = request.form.get('author_disctiption')
        email = request.form.get('author_email')
        phone = request.form.get('author_phone')
        
        # Basic validation
        if not author_name:
            flash("Author name is required!", "error")
            return redirect(url_for('add_author'))
        if not author_disctiption:
            flash("Description is required!", "error")
            return redirect(url_for('add_author'))
        
        # Database connection and insertion
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO author (author_name, author_disctiption, author_email, author_phone) VALUES (%s, %s, %s, %s)",
                (author_name, author_disctiption, email, phone)
            )
            connection.commit()
            flash("Author added successfully!", "success")
        except pymysql.MySQLError as e:
            flash(f"An error occurred: {e}", "error")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
        
        return redirect(url_for('add_author'))  # Redirect after successful insertion

    # Fetch authors to display
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM author")
    authors = cursor.fetchall()
    cursor.close()
    connection.close()
    print(authors)
    # Render the form if the request method is GET
    return render_template('add_author.html', authors=authors)



def MinMax_by_isbn(isbn):
    cursor = db.cursor()
    cursor.callproc('GetBookFormatPrices', (isbn,))
    minmax = cursor.fetchall()
    cursor.close()
    minmax_prices = [{'isbn': row[0], 'format_title': row[1],'min_price': row[2], 'max_price': row[3]} for row in minmax]
    prices = {}
    for row in minmax_prices:
        isbn = row['isbn']
        if isbn not in prices:
            prices[isbn] = {
                "isbn": isbn,
                "format_title": row['format_title'],
                "min_price": row['min_price'],
                "max_price": row['max_price'],
            }

    prices = list(prices.values())
    return prices
# Function to fetch all books from the database
def fetch_books():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM allbooks;")
    allbooks = cursor.fetchall()
    cursor.close()
    
    
    allbooks = [{'isbn': row[0], 'title': row[2],'popularity': row[3], 'author_name': row[4],'price': row[1], 
     'image_path':row[6],'genre_title':row[5],'format_title':row[7],'condition_title':row[8]} for row in allbooks]
    books = {}
    for row in allbooks:
        isbn = row['isbn']
        if isbn not in books:
            books[isbn] = {
                "isbn": isbn,
                "title": row['title'],
                "popularity": row['popularity'],
                "author_name": row['author_name'],
                "genre_title": row['genre_title'],
                "image_path": row['image_path'],
                "condition_title": row['condition_title'],
                "format_title": row['format_title'],

                
                "prices": []
            }
        books[isbn]["prices"].append({"price": row["price"], "format": row["format_title"],"condition":row["condition_title"]})

    books = list(books.values())
    return books
def fetch_book_by_isbn(isbn):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM allbooks WHERE isbn = %s", (isbn,))
    row = cursor.fetchone()
    cursor.close()
    book = {'isbn': row[0], 'title': row[2],'popularity': row[3], 'author_name': row[4],'price': row[1], 
     'image_path':row[6],'genre_title':row[5],'format_title':row[7],'condition_title':row[8]} 
    if book:
        # Initialize the `books` dictionary
        books = {}
        isbn = book['isbn']
        print("print isbn",isbn)
        books[isbn] = {
            "isbn": isbn,
            "title": book['title'],
            "popularity": book['popularity'],
            "author_name": book['author_name'],
            "genre_title": book['genre_title'],
            
            "image_path": book['image_path'],
            "prices": []
        }
        
        # Add price information
        books[isbn]["prices"].append({
            "price": book["price"],
            "format": book["format_title"],
            "condition": book["condition_title"]
        })
    else:
        books = None  # Handle the case if no data is found
    print("Fetched row:", book) 
    return books


def fetch_book_by_param(isbn=None, genre_ids=None,format_ids=None, author_name=None, min_price=None, max_price=None):
    cursor = db.cursor()
    query = "SELECT * FROM allbooks WHERE 1=1"
    params = []
    print("min_price",min_price)
    # Add condition for ISBN
    if isbn:
        query += " AND isbn = %s"
        params.append(isbn)

    # Add condition for multiple genre IDs
    if genre_ids:
        placeholders = ', '.join(['%s'] * len(genre_ids))
        query += f" AND genre_id IN ({placeholders})"
        params.extend(genre_ids)
        print("params:genrid",params)

    # Add condition for multiple format IDs
    if format_ids:
        placeholders = ', '.join(['%s'] * len(format_ids))
        print(placeholders)
        query += f" AND format_id IN ({placeholders})"
        params.extend(format_ids)
        print("params:formatid",params)

    # Add condition for author name (partial match)
    if author_name:
        query += " AND author_name LIKE %s"
        params.append(f"%{author_name}%")
    # Add price range filter
    if min_price:
        query += " AND price >= %s"
        print("query:",query)
        params.append(min_price)
    if max_price:
        query += " AND price <= %s"
        params.append(max_price)
    print(min_price)
    # Execute query and fetch results
    cursor.execute(query, params)
    allbooks = cursor.fetchall()
    allbooks = [{'isbn': row[0], 'title': row[2],'popularity': row[3], 'author_name': row[4],'price': row[1], 
     'image_path':row[6],'genre_title':row[5],'format_title':row[7],'condition_title':row[8],'genre_id':row[9],'format_id':row[11]} for row in allbooks]
   
    books = {}
    for row in allbooks:
        
        isbn = row['isbn']
        print('isbn:',isbn)
        if isbn not in books:
            formats_dicts = []
            cursor.callproc('GetBookFormatPrices', (isbn,))
            formats = cursor.fetchall()

            for format_row in formats:
                # Ensure format_row is for the correct book
                if format_row[0] == isbn:
                    formats_dicts.append({
                        "isbn": format_row[0],
                        "min_price": format_row[1],
                        "max_price": format_row[2]
                    })
            # Initialize the book entry with formats and other details
            books[isbn] = {
                "isbn": isbn,
                "title": row['title'],
                "popularity": row['popularity'],
                "author_name": row['author_name'],
                "genre_title": row['genre_title'],
                "condition": row['condition_title'],
                "image_path": row['image_path'],
                "formats": formats_dicts,
                "prices": []
            }
        
    cursor.close()

    books = list(books.values())
    return books
    


   


@app.route('/allbooks')
def allbooks():
    
    cursor = db.cursor()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    print("min_price is:",min_price)
    # Fetch genres
    cursor.execute("SELECT genre_id, genre_title FROM Genre")
    genres = [{'genre_id': row[0], 'genre_title': row[1]} for row in cursor.fetchall()]
    
    # Fetch formats
    cursor.execute("SELECT format_id, format_title FROM Bookformat")
    formats = [{'format_id': row[0], 'format_title': row[1]} for row in cursor.fetchall()]
    cursor.close()

    # Extract selected genres and formats from query parameters
    selected_genres = request.args.getlist('genre_id')  # List of selected genre IDs
    selected_formats = request.args.getlist('format_id')
    author_name = request.args.get('author_name', '').strip()  # Get author name, strip whitespace  # List of selected format IDs

    # Fetch books based on selected genres and formats
    if not selected_genres and not selected_formats and not author_name and not min_price and not max_price:
        books = fetch_book_by_param()
    else:
        print(min_price)
        books = fetch_book_by_param(genre_ids=selected_genres, format_ids=selected_formats,author_name=author_name,min_price=min_price,
        max_price=max_price)
  
    return render_template(
        'allbooks.html',
        books=books,
        selected_genres=selected_genres,
        selected_formats=selected_formats,
        genres=genres,
         author_name=author_name,
        formats=formats,
        min_price=min_price,
        max_price=max_price
    )
def fetch_book_by_param_managings(genre_ids=None, author_name=None):
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    # Base SQL query with LEFT JOINs
    query = """
    SELECT 
        b.isbn,
        b.title ,
        b.image_path,
        GROUP_CONCAT(DISTINCT a.author_name SEPARATOR ', ') AS authors,
        g.genre_title,
        p.publisher_name
    FROM book b
    LEFT JOIN book_author ba ON b.isbn = ba.isbn
    LEFT JOIN author a ON ba.author_id = a.author_id
    LEFT JOIN genre g ON b.genre_id = g.genre_id
    LEFT JOIN publisher p ON b.publisher_id = p.publisher_id
    WHERE 1=1
    """
    
    # Add filters dynamically based on parameters
    params = []
    
    if genre_ids:
        query += " AND g.genre_id IN (%s)" % ', '.join(['%s'] * len(genre_ids))
        params.extend(genre_ids)
    
    if author_name:
        query += " AND a.author_name LIKE %s"
        params.append(f"%{author_name}%")
    
    # Add GROUP BY and ORDER BY clauses (once only)
    query += """
    GROUP BY 
        b.isbn, 
        b.title, 
        b.image_path,
        g.genre_title,
        p.publisher_name
    ORDER BY 
        b.title
    """
    
    # Execute query
    cursor.execute(query, params)
    books = cursor.fetchall()
    cursor.close()
    
    return books
def fetch_book_by_param_managing(genre_ids=None, author_name=None):
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    # Query to fetch books and pricing information
    query = """
    SELECT 
        b.isbn,
        b.title AS book_title,
        GROUP_CONCAT(DISTINCT a.author_name SEPARATOR ', ') AS authors,
        g.genre_title,
        p.publisher_name,
        bp.pricing_id,
        bp.format_id,
        bf.format_title,
        bp.condition_id,
        bc.condition_title,
        bp.price
    FROM book b
    LEFT JOIN book_author ba ON b.isbn = ba.isbn
    LEFT JOIN author a ON ba.author_id = a.author_id
    LEFT JOIN genre g ON b.genre_id = g.genre_id
    LEFT JOIN publisher p ON b.publisher_id = p.publisher_id
    LEFT JOIN book_pricing bp ON b.isbn = bp.isbn
    LEFT JOIN bookformat bf ON bp.format_id = bf.format_id
    LEFT JOIN bookcondition bc ON bp.condition_id = bc.condition_id
    WHERE 1=1
    """
    
    # Add filters dynamically
    params = []
    if genre_ids:
        query += " AND g.genre_id IN (%s)" % ', '.join(['%s'] * len(genre_ids))
        params.extend(genre_ids)
    
    if author_name:
        query += " AND a.author_name LIKE %s"
        params.append(f"%{author_name}%")
    
    # Group by book information and order by title
    query += """
    GROUP BY 
        b.isbn, 
        b.title, 
        g.genre_title,
        p.publisher_name,
        bp.pricing_id,
        bp.format_id,
        bf.format_title,
        bp.condition_id,
        bc.condition_title,
        bp.price
    ORDER BY 
        b.title
    """
    
    # Execute query
    cursor.execute(query, params)
    books = cursor.fetchall()
    cursor.close()

    # Group pricing information by book
    books_with_pricing = {}
    for row in books:
        isbn = row['isbn']
        if isbn not in books_with_pricing:
            books_with_pricing[isbn] = {
                'isbn': row['isbn'],
                'book_title': row['book_title'],
                'authors': row['authors'],
                'genre_title': row['genre_title'],
                'publisher_name': row['publisher_name'],
                'pricing': []
            }
        # Add pricing details
        if row['pricing_id']:
            books_with_pricing[isbn]['pricing'].append({
                'pricing_id': row['pricing_id'],
                'format_title': row['format_title'],
                'condition_title': row['condition_title'],
                'price': row['price']
            })
    
    return list(books_with_pricing.values())

@app.route('/manage_books', methods=['GET'])
def manage_books():
    cursor = db.cursor()
    
    # Fetch genres
    cursor.execute("SELECT genre_id, genre_title FROM Genre")
    genres = [{'genre_id': row[0], 'genre_title': row[1]} for row in cursor.fetchall()]
    
   

    # Extract selected genres, formats, author, and price range from query parameters
    selected_genres = request.args.getlist('genre_id')  # List of selected genre IDs
    author_name = request.args.get('author_name', '').strip()  # Author name (optional)
    # Prepare the SQL query to fetch books with the necessary details
    query = """
        SELECT 
           distinct( b.isbn), 
            b.title, 
            g.genre_title, 
            p.publisher_name, 
            bf.format_title, 
            bc.condition_title,
            bp.price, 
            b.image_path,
            bi.available_quantity,
            GROUP_CONCAT(a.author_name ORDER BY a.author_name) AS authors
        FROM 
            Book b
        JOIN 
            Genre g ON b.genre_id = g.genre_id
        JOIN 
            Publisher p ON b.publisher_id = p.publisher_id
        JOIN 
            book_pricing bp ON b.isbn = bp.isbn
        JOIN 
            book_inventory bi ON bp.pricing_id = bi.pricing_id
        LEFT JOIN 
            BookFormat bf ON bp.format_id = bf.format_id
        LEFT JOIN 
            Bookcondition bc ON bp.condition_id = bc.condition_id
        LEFT JOIN 
            Book_Author ba ON b.isbn = ba.isbn
        LEFT JOIN 
            Author a ON ba.author_id = a.author_id
    """

    # Add filters for selected genres and author name (if provided)
    if selected_genres:
        query += " WHERE b.genre_id IN (%s)" % ','.join(selected_genres)
    if author_name:
        query += " AND a.author_name LIKE '%%%s%%'" % author_name

    query += " GROUP BY b.isbn,b.image_path, b.title, g.genre_title, p.publisher_name, bf.format_title, bc.condition_title, bp.price, bi.available_quantity"

    # Execute the query to fetch the books
    cursor.execute(query)
    books = cursor.fetchall()

    # Fetch books with or without filters
    books = fetch_book_by_param_managing(
        genre_ids=selected_genres,
        author_name=author_name,
    )
    print(books )
    return render_template(
        'manage_books.html',
        books=books,
        selected_genres=selected_genres,
        genres=genres,
        author_name=author_name,
    )


@app.route('/inventory_consistency_report')
def inventory_consistency_report():
    connection = get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Query to calculate consistency
            query = """
            SELECT 
    b.isbn,
    b.title,
    bp.pricing_id,
    bi.inventory_id,
    bf.format_title AS format_name,
    bc.condition_title AS condition_name,
    bi.quantity AS total_quantity,
    bi.available_quantity,
    (bi.quantity - bi.available_quantity) AS calculated_sold,
    COALESCE(SUM(oi.ordered_quantity), 0) AS transaction_sold,
    CASE 
        WHEN bi.quantity = (bi.available_quantity + COALESCE(SUM(oi.ordered_quantity), 0)) THEN 'Consistent'
        ELSE 'Inconsistent'
    END AS status
FROM book_inventory bi
JOIN book_pricing bp ON bi.pricing_id = bp.pricing_id
JOIN book b ON bp.isbn = b.isbn
JOIN bookformat bf ON bp.format_id = bf.format_id
JOIN bookcondition bc ON bp.condition_id = bc.condition_id
LEFT JOIN orderitem oi ON bp.pricing_id = oi.pricing_id
GROUP BY 
    b.isbn, 
    
    b.title, 
    bi.inventory_id, 
    bf.format_title, 
    bc.condition_title, 
    bi.quantity, 
    bi.available_quantity
ORDER BY b.title, bi.inventory_id;

            """
            cursor.execute(query)
            report = cursor.fetchall()
    finally:
        connection.close()

    return render_template('inventory_consistency_report.html', report=report)

@app.route('/book_managing_detail/<string:isbn>')
def book_managing_detail(isbn):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Retrieve book details
            book_query = """
                SELECT 
                    b.isbn,
                    b.title,
                    GROUP_CONCAT(DISTINCT a.author_name SEPARATOR ', ') AS authors,
                    b.image_path,
                    g.genre_title,
                    p.publisher_name,
                    b.popularity
                FROM book b
                LEFT JOIN book_author ba ON b.isbn = ba.isbn
                LEFT JOIN author a ON ba.author_id = a.author_id
                LEFT JOIN genre g ON b.genre_id = g.genre_id
                LEFT JOIN publisher p ON b.publisher_id = p.publisher_id
                WHERE b.isbn = %s
                GROUP BY 
                    b.isbn, 
                    b.title, 
                    b.image_path, 
                    g.genre_title, 
                    p.publisher_name, 
                    b.popularity
                LIMIT 1
            """
            cursor.execute(book_query, (isbn,))
            book_info = cursor.fetchone()

            # Fetch all formats
            cursor.execute("SELECT format_id, format_title FROM bookformat")
            formats = cursor.fetchall()

            # Fetch all conditions
            cursor.execute("SELECT condition_id, condition_title FROM bookcondition")
            conditions = cursor.fetchall()

            # Retrieve the selected format and condition for the given book
            selected_query = """
                SELECT 
                    bp.format_id, 
                    bc.condition_id,
                    bp.pricing_id
                FROM book_pricing bp
                LEFT JOIN bookcondition bc ON bp.condition_id = bc.condition_id
                WHERE bp.isbn = %s
                LIMIT 1
            """
            cursor.execute(selected_query, (isbn,))
            selected_data = cursor.fetchone()

            # Set selected format and condition
            selected_format_id = selected_data['format_id'] if selected_data else None
            selected_condition_id = selected_data['condition_id'] if selected_data else None
          
            # Retrieve pricing details
            pricing_query = """
                SELECT 
                    format_title,
                    condition_title,
                    price,
                    currentAvailablity,
                    format_id,
                    pricing_id
                FROM Allbooks
                WHERE isbn = %s
                ORDER BY format_title, condition_title
            """
            cursor.execute(pricing_query, (isbn,))
            pricing_rows = cursor.fetchall()
            print(selected_condition_id)
            print(selected_format_id)
    finally:
        connection.close()

    return render_template(
        'book_managing_detail.html',
        book=book_info,
        pricing_rows=pricing_rows,
        formats=formats,
        conditions=conditions,
        selected_format_id=selected_format_id,
        selected_condition_id=selected_condition_id
    )


@app.route('/book_detail/<string:isbn>')
def book_detail(isbn):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Retrieve book details from Allbooks view
            book_query = """
                SELECT 
                    isbn,
                    title,
                    author_name,
                    genre_title,
                    image_path,pricing_id
                    popularity
                FROM Allbooks
                WHERE isbn = %s
                LIMIT 1
            """
            cursor.execute(book_query, (isbn,))
            book_info = cursor.fetchone()

            # Retrieve pricing details from Allbooks view
            pricing_query = """
                SELECT 
                    format_title,
                    condition_title,
                    price,
                    currentAvailablity,
                    format_id,pricing_id
                FROM Allbooks
                WHERE isbn = %s
                ORDER BY format_title, condition_title
            """
            cursor.execute(pricing_query, (isbn,))
            pricing_rows = cursor.fetchall()
    finally:
        connection.close()

    return render_template('book_detail.html', book=book_info, pricing_rows=pricing_rows)
@app.route('/')
def home():
    session.clear()
    logout_user()
    return redirect(url_for('allbooks'))  # Redirect back to home
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == '__main__':
    app.run(debug=True)
