import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns
from credentials import user, password, host, dbname

# set dashboard title
st.title("🏫 College Scorecard Dashboard")

# Add authors in the header
st.markdown("""
### By Team Alexandria
""")

# Sidebar for navigation
st.sidebar.title("Menus")
menu_options = st.sidebar.radio(
    "Choose a visualization:",
    options=["🗒️ Table 1: Overview of Dataset", "🗒️ Table 2: Number of Institutions by Type and Region",
             "🗒️ Table 3: Tuition Rates by State and CC", "🗒️ Table 4: Loan Repayment Performance",
             "🗒️ Table 5: Admission and Students", "📈Plot 1: Trends in Tuition and Loan Repayment Rates",
             "🌏 Plot 2: Tuition Rates Across the U.S."]
)

#need to add: "📈Plot 3: Academic and Earnings Insights", "📈Plot 4: Faculty and Graduation Trends"

# create a dropdown for year selection
selected_year = st.selectbox(
    "Select a year to display data:",
    options=[2019, 2020, 2021, 2022],
    index=0  # Default to the first option
)
st.write(f"Displaying data for the year: {selected_year}")

# Connect to the database
try:
    conn = psycopg2.connect(
        host=host,
        dbname=dbname,
        user=user,
        password=password
    )
    st.success("Database connection established!")
except Exception as e:
    st.error(f"Error connecting to the database: {e}")
    st.stop()

cursor = conn.cursor()

# Table 1: Overview of Dataset
if menu_options == "🗒️ Table 1: Overview of Dataset":
    st.subheader("🗒️ Table 1: Overview of Dataset")

    # Define the list of interested opeids
    interested_opeids = [
        "00324200",  # CMU
        "00297400",  # UNC
        "00215500",  # Harvard
        "00131500",  # UCLA
        "00144500",  # Georgetown
        "00130500",  # Stanford
        "00185600",  # Cornell
        "00278500",  # NYU
        "00142600",  # Yale
        "00340100"   # Brown
    ]

    placeholders = ', '.join(['%s'] * len(interested_opeids))

    # Query
    query_tb1 = f"""
    SELECT
        institution.*,
        tuition.year,
        tuition.tuitionfee_in,
        tuition.tuitionfee_out,
        admission.adm_rate,
        graduation.ugnonds,
        graduation.grads
    FROM
        institution
    LEFT JOIN tuition
        ON institution.opeid = tuition.opeid
    LEFT JOIN admission
        ON institution.opeid = admission.opeid
        AND tuition.year = admission.year
    LEFT JOIN graduation
        ON institution.opeid = graduation.opeid
        AND tuition.year = graduation.year
    WHERE tuition.year = %s
    AND institution.opeid IN ({placeholders});
    """

    # Execute the query
    try:
        query_params = [selected_year] + interested_opeids
        cursor.execute(query_tb1, query_params)
        data = cursor.fetchall()

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Create a DataFrame
        df_institution = pd.DataFrame(data, columns=columns)

        # Display the data in Streamlit
        st.write("### Table (Filtered by Specific OPEIDs)")
        st.write(df_institution)

    except Exception as e:
        st.error(f"Error executing the query: {e}")

if menu_options == "🗒️ Table 2: Number of Institutions by Type and Region":
    st.subheader("🗒️ Table 2: Number of Institutions by Type and Region")

    # Query to join institution and tuition tables
    query_tb2 = """
        SELECT
            institution.INSTNM AS institution_name,
            institution.control,
            institution.region,
            institution.latitude,
            institution.longitud,
            tuition.tuitionfee_in,
            tuition.COSTT4_A AS total_cost,
            tuition.year
        FROM tuition
        LEFT JOIN institution
        ON tuition.opeid = institution.opeid
        WHERE tuition.year = %s;
    """

    # Execute the query
    try:
        cursor.execute(query_tb2, (selected_year,))
        data = cursor.fetchall()

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Create a DataFrame
        df = pd.DataFrame(data, columns=columns)

        if not df.empty:
            # Summarize by Type of Institution
            summary_by_type = df.groupby("control").size().reset_index(name="Number of Institutions")
            summary_by_type["control"] = summary_by_type["control"].map({
                1: "Public",
                2: "Private Nonprofit",
                3: "Private For-Profit"
            })

            # Summarize by Region
            summary_by_region = df.groupby("region").size().reset_index(name="Number of Institutions")
            summary_by_region["region"] = summary_by_region["region"].map({
                0: "US Service Schools",
                1: "New England",
                2: "Mid East",
                3: "Great Lakes",
                4: "Plains",
                5: "Southeast",
                6: "Southwest",
                7: "Rocky Mountains",
                8: "Far West",
                9: "Outlying Areas"
            })

            # Display the summaries
            st.write("### By Type")
            st.dataframe(summary_by_type)

            st.write("### By Region")
            st.dataframe(summary_by_region)
        else:
            st.warning("No data available for the selected year.")

    except Exception as e:
        st.error(f"Error executing the query for Table 2: {e}")

if menu_options == "🗒️ Table 3: Tuition Rates by State and CC":
    st.subheader("🗒️ Table 3: Tuition Rates by State and CC")

    # Query to join institution and tuition tables
    query_tb3 = """
        SELECT
            institution.region AS state,
            institution.c21basic AS carnegie_classification,
            AVG(tuition.tuitionfee_in) AS avg_in_state_tuition,
            AVG(tuition.tuitionfee_out) AS avg_out_of_state_tuition
        FROM tuition
        LEFT JOIN institution
        ON Tuition.opeid = Institution.opeid
        WHERE Tuition.year = %s
        GROUP BY institution.region, institution.c21basic
        ORDER BY institution.region, institution.c21basic;
    """

    # Execute the query
    cursor.execute(query_tb3, (selected_year,))
    data = cursor.fetchall()

    # Get column names
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)

    st.subheader(f"By State and Carnegie Classification")
    st.dataframe(df)

if menu_options == "🗒️ Table 4: Loan Repayment Performance":
    st.subheader("🗒️ Table 4: Loan Repayment Performance")

    # Query to join institution and tuition tables
    query_tb4 = """
        WITH FinancialPerformance AS (
        SELECT
            Tuition.opeid,
            Institution.instnm AS institution_name,
            AVG(Loan.dbrr5_fed_ug_rt) AS avg_loan_repayment_rate
        FROM Tuition
        LEFT JOIN Loan ON Tuition.opeid = Loan.opeid
        LEFT JOIN Institution ON Tuition.opeid = Institution.opeid
        WHERE Tuition.year = %s
        GROUP BY Tuition.opeid, Institution.instnm
    ),
    BestWorstPerforming AS (
        SELECT * FROM (
            SELECT
                *,
                'Best Performing' AS performance_category
                FROM FinancialPerformance
                ORDER BY avg_loan_repayment_rate DESC
                LIMIT 1
        ) AS Best
        UNION ALL
        SELECT * FROM (
            SELECT
                *,
                'Worst Performing' AS performance_category
                FROM FinancialPerformance
                ORDER BY avg_loan_repayment_rate ASC
                LIMIT 1
        ) AS Worst
    )
    SELECT
        performance_category,
        institution_name,
        avg_loan_repayment_rate
        FROM BestWorstPerforming;
    """

    # Execute the query
    try:
        cursor.execute(query_tb4, (selected_year,))
        data = cursor.fetchall()

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Create a DataFrame
        df = pd.DataFrame(data, columns=columns)

        # Highlight best and worst performing rows
        def highlight_performance(row):
            if row['performance_category'] == 'Best Performing':
                return ['background-color: lightgreen'] * len(row)
            elif row['performance_category'] == 'Worst Performing':
                return ['background-color: lightcoral'] * len(row)
            else:
                return [''] * len(row)

        # Display the data in Streamlit with styling
        st.write("### Best and Worst Performing Institutions")
        st.dataframe(df.style.apply(highlight_performance, axis=1))

    except Exception as e:
        st.error(f"Error executing the query for Table 4: {e}")

if menu_options == "🗒️ Table 5: Admission and Students":
    st.subheader("🗒️ Table 5: Admission and Students")

    # Query to join institution and admission tables
    query_tb5 = """
        SELECT
            institution.INSTNM AS institution_name,
            admission.adm_rate, admission.satvrmid,
            admission.year,
            graduation.ugnonds, graduation.grads
        FROM admission
        LEFT JOIN institution
        ON admission.opeid = institution.opeid
        LEFT JOIN graduation
        ON admission.opeid = graduation.opeid
        AND admission.year = graduation.year
        WHERE admission.adm_rate IS NOT NULL
        AND admission.year = %s
        ORDER BY adm_rate DESC
        LIMIT 10;
    """

    cursor.execute(query_tb5, (selected_year,))
    data = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    st.dataframe(df)

if menu_options == "📈Plot 1: Trends in Tuition and Loan Repayment Rates":
    st.subheader("📈Plot 1: Trends in Tuition and Loan Repayment Rates")

    query_pl1 = """
        SELECT
        tuition.year,
        AVG(tuition.tuitionfee_in) AS avg_in_state_tuition,
        AVG(loan.dbrr5_fed_ug_rt) AS avg_loan_repayment_rate
        FROM Tuition
        LEFT JOIN Loan
        ON Tuition.opeid = Loan.opeid AND Tuition.year = Loan.year
        GROUP BY tuition.year
        ORDER BY tuition.year;
    """
    cursor.execute(query_pl1)
    data = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]
    df2 = pd.DataFrame(data, columns=columns)

    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Average In-State Tuition ($)", color="blue")
    ax1.plot(df2["year"], df2["avg_in_state_tuition"], color="blue", label="Avg Tuition")
    ax1.tick_params(axis="y", labelcolor="blue")

    ax2 = ax1.twinx()
    ax2.set_ylabel("Average Loan Repayment Rate (%)", color="orange")
    ax2.plot(df2["year"], df2["avg_loan_repayment_rate"], color="orange", label="Repayment Rate")
    ax2.tick_params(axis="y", labelcolor="orange")

    plt.title("Trends in Tuition and Loan Repayment Rates Over Time")
    fig.tight_layout()
    st.pyplot(fig)

    # Define and execute query_pl1_2
    query_pl1_2 = """
    WITH MostExpensive AS (
        SELECT
            tuition.opeid,
            institution.instnm AS institution_name,
            AVG(tuition.tuitionfee_in) AS avg_in_state_tuition
        FROM Tuition
        LEFT JOIN Institution
        ON Tuition.opeid = Institution.opeid
        GROUP BY tuition.opeid, institution.instnm
        ORDER BY avg_in_state_tuition DESC
        LIMIT 5
    )
    SELECT
        tuition.year,
        tuition.opeid,
        institution.instnm AS institution_name,
        tuition.tuitionfee_in AS in_state_tuition,
        tuition.tuitionfee_out AS out_of_state_tuition,
        loan.dbrr5_fed_ug_rt AS loan_repayment_rate
    FROM Tuition
    LEFT JOIN Loan
    ON Tuition.opeid = Loan.opeid AND Tuition.year = Loan.year
    LEFT JOIN Institution
    ON Tuition.opeid = Institution.opeid
    WHERE Tuition.opeid IN (SELECT opeid FROM MostExpensive)
    ORDER BY tuition.year, tuition.opeid;
    """

    cursor.execute(query_pl1_2)
    data = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]
    df_selected = pd.DataFrame(data, columns=columns)

    st.subheader("Trends in Tuition and Loan Repayment for Selected Institutions")

    plt.figure(figsize=(12, 8))
    sns.lineplot(
        data=df_selected,
        x="year",
        y="in_state_tuition",
        hue="institution_name",
        marker="o",
        palette="tab10"
    ).set(title="In-State Tuition Trends", ylabel="In-State Tuition ($)")
    st.pyplot(plt)

    plt.figure(figsize=(12, 8))
    sns.lineplot(
        data=df_selected,
        x="year",
        y="loan_repayment_rate",
        hue="institution_name",
        marker="o",
        palette="tab10"
    ).set(title="Loan Repayment Trends", ylabel="Repayment Rate (%)")
    st.pyplot(plt)

if menu_options == "🌏 Plot 2: Tuition Rates Across the U.S.":
    st.subheader("🌏 Plot 2: Tuition Rates Across the U.S.")

    query_pl2 = """
    SELECT
        institution.INSTNM,
        institution.control,
        institution.region,
        institution.latitude,
        institution.longitud,
        tuition.tuitionfee_in,
        tuition.COSTT4_A,
        tuition.year
    FROM tuition
    LEFT JOIN institution
    ON tuition.opeid = institution.opeid
    WHERE tuition.year = %s;
    """
    cursor.execute(query_pl2, (selected_year,))
    data = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    df = df.rename(columns={"longitud": "longitude"})

    map_data = df.dropna(subset=["latitude", "longitude"])
    map_data["latitude"] = map_data["latitude"].apply(float)
    map_data["longitude"] = map_data["longitude"].apply(float)
    st.map(map_data, size="tuitionfee_in")


# close database connection
cursor.close()
conn.close()
st.info("Database connection closed.")