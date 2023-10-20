from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
from datetime import datetime, timedelta, date
import matplotlib.pyplot as plt
import numpy as np
import io
from base64 import b64encode

app = Flask(__name__)

today = pd.Timestamp(datetime.now().strftime('%Y-%m-%d'))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard', methods=['POST'])
def dashboard():
    inventory_file = request.files['inventory_file']
    order_file = request.files['order_file']
    
    # Save uploaded files
    inventory_file.save('inventory.csv')
    order_file.save('orders.csv')
    
    df1 = pd.read_csv('inventory.csv')
    df = pd.read_csv('orders.csv')
    
    # Rest of the code to generate the graph and new_df CSV
    new_df = pd.DataFrame({'asin': df['asin'].drop_duplicates(), 'sku': df['sku'], 'product-name': df['product-name']})
    new_df = new_df.dropna(subset=['asin'])

    # Filter out cancelled orders
    df = df[df['order-status'] != 'Cancelled'].copy()

    date_format = '%d-%m-%Y %H:%M'

    for index,row in df.iterrows():
        datetime_obj = datetime.strptime(row['purchase-date'], date_format)
        df.at[index, 'purchase-date'] = datetime_obj

    # Get today's date
    # today = pd.Timestamp(datetime.now().strftime('%Y-%m-%d'))

    # Calculate the date 30 days ago
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days =7)
    fifteen_days_ago = today - timedelta(days =15)
    one_days_ago = today - timedelta(days =1)

    lst_date = {'Today':today,  'Yesterday': one_days_ago,  'in_7_days': seven_days_ago,  'in_15_days': fifteen_days_ago, 'in_30_days': thirty_days_ago}
    
    asin_quantity = {}

    for key, value in lst_date.items():
        for asin in df['asin'].unique():
            df_temp = df[(df['asin'] == asin) & (df['purchase-date'] >= value) & (df['purchase-date'] <= today)]
            quantity = df_temp['quantity'].sum()
            asin_quantity[asin] = quantity
            for index, row in new_df.iterrows():
                for key1, value1 in asin_quantity.items():
                    if key1 == row['asin']:
                        new_df.at[index, key] = value1

    for index, row in new_df.iterrows():
        quant = 0
        for index1, row1 in df1.iterrows():
            if row1['asin'] == row['asin'] and row1['Warehouse-Condition-code'] == 'SELLABLE':
                quant += row1['Quantity Available']
            elif row1['asin'] == row['asin'] and row1['Warehouse-Condition-code'] == 'UNSELLABLE':
                quant -= row1['Quantity Available']
                
        if quant >= 0:
            new_df.at[index, 'Quantity Available'] = quant
        else:
            new_df.at[index, 'Quantity Available'] = 0

    lst_order_asin = list(new_df['asin'])

    new_row = {}

    for index1, row1 in df1.iterrows():
        quant_new = 0
        if row1['asin'] in lst_order_asin:
            continue
        else:
            if row1['Warehouse-Condition-code'] == 'SELLABLE':
                quant_new += row1['Quantity Available']
            elif row1['Warehouse-Condition-code'] == 'UNSELLABLE':
                quant_new -= row1['Quantity Available']
                
            if quant_new >= 0:
                quant_new = quant_new
            else:
                quant_new = 0
        
            new_row = {
                'asin': row1['asin'],
                'sku': row1['seller-sku'],
                'product-name': '',
                'Today': 0,
                'Yesterday': 0,
                'in_7_days': 0,
                'in_15_days': 0,
                'in_30_days': 0,
                'Quantity Available': quant_new
            }
            
            new_df = pd.concat([new_df, pd.DataFrame([new_row])])

    # Filter rows where either 'in_30_days' or 'quantity_available' is non-zero
    df_filtered = new_df[(new_df['in_30_days'] != 0) | (new_df['Quantity Available'] != 0)]

    filename = 'new_df' + '_'+ today.strftime('%d-%m-%Y') + '.csv'

    # Save new_df to a CSV file
    new_df.to_csv(filename, index=False)
    
    # Prepare the graph
    x = np.arange(len(df_filtered))
    width = 0.35  # width of the bars

    # Plot the graph
    fig, ax = plt.subplots(figsize=(12, 7))

    ax.bar(x - width/2, df_filtered['in_30_days'], width, label='In 30 Days', color='orange')
    ax.bar(x + width/2, df_filtered['Quantity Available'], width, label='Quantity Available', color='blue', alpha=0.5)

    # Rotate x-axis labels
    ax.set_xticks(x)
    ax.set_xticklabels(df_filtered['asin'], rotation=45, ha='right')

    # Add labels and title
    plt.xlabel('ASIN')
    plt.ylabel('Value')
    plt.title('Graph of Order vs Inventory (Non-Zero Values)')
    plt.legend()

    # Save the graph to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Clear the graph from memory
    plt.close()

    # return render_template('dashboard.html', image=buf.getvalue())
    return render_template('dashboard.html', image=b64encode(buf.getvalue()).decode('utf-8'))


@app.route('/download')
def download():
    # Return the new_df CSV file for download
    get_it = 'new_df' + '_'+ today.strftime('%d-%m-%Y') + '.csv'
    return send_file(get_it, as_attachment=True)


if __name__ == "__main__":
    app.run(debug = True)