import func.generator as g

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Run:

"""
Generate full sales data by merging customer, product, and order data,
then export the merged data to a CSV file.

This function performs the following steps:
1. Logs the start of data preparation.
2. Generates customer data.
3. Retrieves the minimum and maximum customer IDs.
4. Generates product data.
5. Retrieves the minimum and maximum product IDs.
6. Generates order data using customer and product ID ranges.
7. Merges order data with product and customer data.
8. Adds a calculated column for gross revenue.
9. Sorts the merged data by order date.
10. Logs the completion of data preparation.
11. Exports the sorted data to a CSV file.
12. Logs the success of the file save operation.
"""
g.generate_full_sales_data()