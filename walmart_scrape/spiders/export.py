# import csv
# import psycopg2
# from psycopg2 import sql

# # PostgreSQL connection parameters
# db_params = {
#     'host': 'db.sxoqzllwkjfluhskqlfl.supabase.co',
#     'database': 'postgres',
#     'user': 'postgres',
#     'password': '5giE*5Y5Uexi3P2',
# }

# # SQL query
# sql_query = """
#     SELECT * FROM "public"."walmart_product"
#     WHERE sys_run_date = (SELECT MAX(sys_run_date) FROM "public"."walmart_product")
# """

# # Output CSV file path
# csv_file_path = 'output_walmart.csv'

# # Connect to the PostgreSQL database
# conn = psycopg2.connect(**db_params)

# try:
#     # Create a cursor object
#     cursor = conn.cursor()

#     # Execute the SQL query
#     cursor.execute(sql_query)

#     # Fetch all the rows
#     rows = cursor.fetchall()

#     # Get the column names
#     column_names = [desc[0] for desc in cursor.description]

#     # Write data to CSV file
#     with open(csv_file_path, 'w', newline='') as csv_file:
#         csv_writer = csv.writer(csv_file)
        
#         # Write header
#         csv_writer.writerow(column_names)
        
#         # Write data
#         csv_writer.writerows(rows)

#     print(f'Data exported to {csv_file_path}')

# finally:
#     # Close the cursor and connection
#     cursor.close()
#     conn.close()
