import streamlit as st
import pandas as pd
from database import run_query

st.set_page_config(page_title="Sales Intelligence Hub", layout="wide")

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.title("🔐 Sales Intelligence Hub - Login")
    
    with st.form("login_form"):
        username = st.text_input("username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # Check user in TiDB
            user = run_query("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user[0]
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid Username or Password")

# --- DASHBOARD PAGE ---
else:
    user = st.session_state.user
    st.sidebar.title(f"Welcome, {user['username']}")
    st.sidebar.write(f"Role: {user['role']}")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("📊 Sales Dashboard")

    # ROLE-BASED ACCESS CONTROL (RBAC) Logic
    if user['role'] == 'Super Admin':
        sales_query = "SELECT * FROM customer_sales"
    else:
        # Admin can only see their branch
        sales_query = f"SELECT * FROM customer_sales WHERE branch_id = {user['branch_id']}"

    data = run_query(sales_query)

    if data:
        df = pd.DataFrame(data)

        # Display KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sales", f"₹{df['gross_sales'].sum():,.2f}")
        col2.metric("Received", f"₹{df['received_amount'].sum():,.2f}")
        col3.metric("Pending", f"₹{df['pending_amount'].sum():,.2f}")

        st.subheader("Recent Transactions")
        st.dataframe(df)
    else:
        st.info("No sales data found for this branch.")
        df = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["📊 View Dashboard", "➕ Add New Sale", "💰 Record Payment"])

    with tab1:
        st.subheader("Branch Sales Overview")
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Sales", f"₹{df['gross_sales'].sum():,.2f}")
            col2.metric("Received", f"₹{df['received_amount'].sum():,.2f}")
            col3.metric("Pending", f"₹{df['pending_amount'].sum():,.2f}")
            st.dataframe(df)

            st.markdown("---")
            st.subheader("📈 Advanced Analytics")

            total_sales = df['gross_sales'].sum()
            total_pending = df['pending_amount'].sum()
            pending_pc = (total_pending / total_sales) * 100 if total_sales > 0 else 0

            col1, col2 = st.columns(2)
            col1.metric("Pending Collection %", f"{pending_pc:.1f}%", delta=f"{pending_pc:.1f}%", delta_color="inverse")

            with col2:
                st.write("**Sales by Branch**")
                branch_data = df.groupby("branch_id")["gross_sales"].sum()
                st.bar_chart(branch_data)

            st.write("### 💰 Payment Method Analysis")
            pay_data = run_query("SELECT payment_method, SUM(amount_paid) as total FROM payment_splits GROUP BY payment_method")
            if pay_data:
                pay_df = pd.DataFrame(pay_data)
                st.bar_chart(pay_df.set_index("payment_method"))
        else:
            st.info("No sales data found.")

    
    
    with tab2:
        st.subheader("Register a New Sale")
        with st.form("new_sale_form", clear_on_submit=True):
            name = st.text_input("Customer Name")
            mobile = st.text_input("Mobile Number")
            branch = st.number_input("Branch ID", min_value=1, step=1) 
            product = st.selectbox("Product", ["TV", "BA", "FSD"])
            amount = st.number_input("Gross Amount", min_value=0.0)
            
            if st.form_submit_button("Register Sale"):
                if name and mobile and branch:
                    try:
                        # This query now matches the 5 variables we are sending
                        query = """
                            INSERT INTO customer_sales (branch_id, name, mobile_number, product_name, gross_sales, date) 
                            VALUES (%s, %s, %s, %s, %s, CURDATE())
                        """
                        # The variables in this tuple must match the %s order above
                        run_query(query, (branch, name, mobile, product, amount))
                        
                        st.success(f"✅ Successfully registered {name}!")
                        st.rerun() # Refresh the dashboard to show the new data
                    except Exception as e:
                        st.error(f"❌ Database Error: {e}")
                else:
                    st.warning("⚠️ Please fill in all fields (Name, Mobile, and Branch).")

    with tab3:
        st.subheader("💰 Record a Customer Payment")
        with st.form("payment_form"):
            sale_id = st.number_input("Enter Sale ID (from Dashboard)", min_value=1)
            pay_amt = st.number_input("Amount Paid (₹)", min_value=0.0)
            method = st.selectbox("Payment Method", ["UPI", "Cash", "Card", "Net Banking"])

            submitted = st.form_submit_button("Confirm Payment")

            if submitted:
                pay_query = """
                    INSERT INTO payment_splits (sale_id, payment_date, amount_paid, payment_method) 
                    VALUES (%s, CURDATE(), %s, %s)
                """
                run_query(pay_query, (sale_id, pay_amt, method))

                update_sales = """
                    UPDATE customer_sales 
                    SET received_amount = received_amount + %s 
                    WHERE sale_id = %s
                """
                run_query(update_sales, (pay_amt, sale_id))

                st.success(f"Successfully recorded ₹{pay_amt} for Sale #{sale_id}!")
                st.rerun()
                