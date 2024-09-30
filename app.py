import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import streamlit as st
from wordcloud import WordCloud
## Load Data
customers_df = pd.read_csv("data/customers_dataset.csv")
products_df = pd.read_csv("data/products_dataset.csv")
category_df = pd.read_csv("data/product_category_name_translation.csv")
sellers_df = pd.read_csv("data/sellers_dataset.csv")
orders_df = pd.read_csv("data/orders_dataset.csv")
order_items_df = pd.read_csv("data/order_items_dataset.csv")
order_payments_df = pd.read_csv("data/order_payments_dataset.csv")
order_reviews_df = pd.read_csv("data/order_reviews_dataset.csv")
geolocation_df = pd.read_csv("data/geolocation_dataset.csv")
## Clean data
def clean_data():
    geolocation_df.drop_duplicates(inplace=True)
    products_df['product_category_name'].fillna("unknown", inplace=True)
    category_df.loc[-1] = ["unknown", "unknown"]
    products_df['product_name_lenght'].fillna(0, inplace=True)
    products_df['product_description_lenght'].fillna(0, inplace=True)
    products_df['product_photos_qty'].fillna(0, inplace=True)
    products_df['product_weight_g'].fillna(0, inplace=True)
    products_df['product_length_cm'].fillna(0, inplace=True)
    products_df['product_height_cm'].fillna(0, inplace=True)
    products_df['product_width_cm'].fillna(0, inplace=True)

    orders_df['order_purchase_timestamp'] = pd.to_datetime(orders_df['order_purchase_timestamp'])
    orders_df['order_approved_at'] = pd.to_datetime(orders_df['order_approved_at'])
    orders_df['order_delivered_carrier_date'] = pd.to_datetime(orders_df['order_delivered_carrier_date'])
    orders_df['order_delivered_customer_date'] = pd.to_datetime(orders_df['order_delivered_customer_date'])

    approved_durations = orders_df['order_approved_at'] - orders_df['order_purchase_timestamp']
    approved_durations = approved_durations.dropna() 
    average_approved_duration = approved_durations.mean()

    missing_approved_mask = orders_df['order_approved_at'].isna()
    orders_df.loc[missing_approved_mask, 'order_approved_at'] = (
        orders_df.loc[missing_approved_mask, 'order_purchase_timestamp'] + average_approved_duration
    )

    carrier_durations = orders_df['order_delivered_carrier_date'] - orders_df['order_purchase_timestamp']
    carrier_durations = carrier_durations.dropna() 
    average_carrier_duration = carrier_durations.mean()

    missing_carrier_mask = orders_df['order_delivered_carrier_date'].isna()
    orders_df.loc[missing_carrier_mask, 'order_delivered_carrier_date'] = (
        orders_df.loc[missing_carrier_mask, 'order_purchase_timestamp'] + average_carrier_duration
    )

    customer_durations = orders_df['order_delivered_customer_date'] - orders_df['order_purchase_timestamp']
    customer_durations = customer_durations.dropna()  
    average_customer_duration = customer_durations.mean()

    missing_customer_mask = orders_df['order_delivered_customer_date'].isna()
    orders_df.loc[missing_customer_mask, 'order_delivered_customer_date'] = (
        orders_df.loc[missing_customer_mask, 'order_purchase_timestamp'] + average_customer_duration
    )

    order_reviews_df['review_comment_title'].fillna("", inplace=True)
    order_reviews_df['review_comment_message'].fillna("", inplace=True)

sns.set_theme(style='dark')

clean_data()

min_date = orders_df["order_purchase_timestamp"].min()
max_date = orders_df["order_purchase_timestamp"].max()

st.title("E-Commerce Dashboard")

with st.sidebar:
    
    # Mengambil start_date & end_date dari date_input
    start_date, end_date = st.date_input(
        label='Date Range',min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

main_orders_df = orders_df[(orders_df["order_purchase_timestamp"] >= str(start_date)) & 
                (orders_df["order_purchase_timestamp"] <= str(end_date))]


def create_by_category_df(is_top):
    products_and_sale = pd.merge(order_items_df, main_orders_df[['order_id', 'order_purchase_timestamp']], on='order_id')
    products_and_sale = products_and_sale.groupby(by="product_id").count()['order_id'].reset_index()
    products_and_sale = pd.merge(products_and_sale, products_df)
    products_and_sale = pd.merge(products_and_sale, category_df)
    sale_by_category = products_and_sale.groupby('product_category_name_english')['order_id'].sum().reset_index(name='number_of_orders')
    top_or_bottom_10 = sale_by_category.sort_values(by='number_of_orders', ascending=not is_top).head(10)
    return top_or_bottom_10


def create_by_location_df(person_type):
    if person_type == "customer":
        person_df = customers_df
    else:
        person_df = sellers_df
    merged_df = pd.merge(person_df, geolocation_df, left_on=f'{person_type}_zip_code_prefix', right_on='geolocation_zip_code_prefix')
    order_and_items_df = pd.merge(main_orders_df, order_items_df)
    merged_df = pd.merge(merged_df, order_and_items_df, on=f'{person_type}_id')

    region_sales = merged_df.groupby(['geolocation_lat', 'geolocation_lng']).size().reset_index(name='number_of_orders')

    gdf = gpd.GeoDataFrame(region_sales, 
                       geometry=gpd.points_from_xy(region_sales['geolocation_lng'], region_sales['geolocation_lat']))
    gdf = gdf.sort_values(by='number_of_orders')
    return gdf

def create_by_time_df(time_type):
    time_df = main_orders_df.copy()
    if time_type == "hour_of_day":
        time_df[time_type] = time_df['order_purchase_timestamp'].dt.hour
    elif time_type == "day_of_week":
        time_df[time_type] = time_df['order_purchase_timestamp'].dt.day_name()
        day_counts = time_df[time_type].value_counts().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        return day_counts
    else:
        time_df[time_type] = time_df['order_purchase_timestamp'].dt.day

    time_counts = time_df[time_type].value_counts().sort_index()
    return time_counts


def create_by_payment_df():
    payment_types = pd.merge(main_orders_df, order_payments_df)
    payment_types = payment_types.groupby("payment_type", as_index=False).agg({
        "order_id": "nunique", 
        "payment_value": "mean",
    })
    return payment_types

with open('data/portuguese_stopwords.txt', 'r', encoding='utf-8') as f:
    stop_words = set(f.read().splitlines())

def filter_stopwords(comment, stop_words):
    words = comment.split()
    filtered_words = [word for word in words if word.lower() not in stop_words]
    return ' '.join(filtered_words)

def create_by_review_df(score):
    merged_df = pd.merge(main_orders_df, order_reviews_df)
    merged_df['filtered_comment_message'] = merged_df['review_comment_message'].apply(lambda x: filter_stopwords(x, stop_words))
    comments = merged_df[merged_df['review_score'] == score]['filtered_comment_message']
    return comments

top10_by_category = create_by_category_df(is_top=True) 
bottom10_by_category = create_by_category_df(is_top=False) 

by_customer_location = create_by_location_df("customer")
by_seller_location = create_by_location_df("seller")

by_hour_of_day = create_by_time_df("hour_of_day")
by_day_of_week = create_by_time_df("day_of_week")
by_date_of_month = create_by_time_df("date_of_month")

by_payment_type = create_by_payment_df()

by_score_1 = create_by_review_df(1)
by_score_2 = create_by_review_df(2)
by_score_3 = create_by_review_df(3)
by_score_4 = create_by_review_df(4)
by_score_5 = create_by_review_df(5)

st.header('Products Category')
tab1, tab2 = st.tabs(["Most Popular", "Least Popular"])

with tab1:
    st.subheader("Most Popular Product Categories")
    with st.container():
        fig, ax = plt.subplots(figsize=(10,6))
        sns.barplot(x=top10_by_category['number_of_orders'], y=top10_by_category['product_category_name_english'], palette='viridis')

        plt.xticks(rotation=90)
        plt.xlabel('Product Category')
        plt.ylabel('Number of Orders')
        plt.title('Top 10 Product Categories by Number of Orders')

        plt.tight_layout()

        st.pyplot(fig)

with tab2:
    st.subheader("Least Popular Product Categories")
    with st.container():
        fig, ax = plt.subplots(figsize=(10,6))
        sns.barplot(x=bottom10_by_category['number_of_orders'], y=bottom10_by_category['product_category_name_english'], palette='viridis')

        plt.xticks(rotation=90)
        plt.xlabel('Product Category')
        plt.ylabel('Number of Orders')
        plt.title('Bottom 10 Product Categories by Number of Orders')

        plt.tight_layout()

        st.pyplot(fig)


world = gpd.read_file("ne/ne_110m_admin_0_countries.shp")

# Filter for Brazil
brazil = world[world['ADMIN'] == 'Brazil']
st.header('Orders Location')
tab3, tab4 = st.tabs(["By Customer", "By Seller"])
with tab3:
    st.subheader("Orders by Customer Regions")
    with st.container():

        fig, ax = plt.subplots(figsize=(12, 10))

        brazil.plot(ax=ax, color='lightgray', edgecolor='black')

        # Ukurang titik jg dipengaruhi jumlah order
        by_customer_location.plot(ax=ax, 
                markersize=by_customer_location['number_of_orders'] / by_customer_location['number_of_orders'].max() * 100, 
                cmap='coolwarm', 
                column='number_of_orders', 
                legend=True)

        plt.title('Top-Performing Regions by Number of Products Bought')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        st.pyplot(fig)

with tab4:
    st.subheader("Orders by Seller Regions")
    with st.container():

        fig, ax = plt.subplots(figsize=(12, 10))

        brazil.plot(ax=ax, color='lightgray', edgecolor='black')

        # Ukurang titik jg dipengaruhi jumlah order
        by_seller_location.plot(ax=ax, 
                markersize=by_seller_location['number_of_orders'] / by_seller_location['number_of_orders'].max() * 100, 
                cmap='coolwarm', 
                column='number_of_orders', 
                legend=True)

        plt.title('Top-Performing Regions by Number of Products Bought')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        st.pyplot(fig)


st.header('Purchases by Time')
tab5, tab6, tab7 = st.tabs(["Hour of the Day", "Day of the Week", "Date of the Month"])

with tab5:
    st.subheader("Purchase Frequency by Hour of the Day")
    with st.container():
        fig, ax = plt.subplots(figsize=(12, 6))
        plt.plot(by_hour_of_day.index, by_hour_of_day.values, marker='o', color='b') 
        plt.title('Number of Transactions based on Hour of the Day')
        plt.xlabel('Hour')
        plt.ylabel('Number of Purchases')
        plt.xticks(rotation=45)
        plt.grid()

        st.pyplot(fig)

with tab6:
    st.subheader("Purchase Frequency by Day of the Week")
    with st.container():
        fig, ax = plt.subplots(figsize=(12, 6))
        plt.plot(by_day_of_week.index, by_day_of_week.values, marker='o', color='b') 
        plt.title('Number of Transactions based on Day of the Week')
        plt.xlabel('Day')
        plt.ylabel('Number of Purchases')
        plt.xticks(rotation=45)
        plt.grid()

        st.pyplot(fig)

with tab7:
    st.subheader("Purchase Frequency by Hour of the Day")
    with st.container():
        fig, ax = plt.subplots(figsize=(12, 6))
        plt.plot(by_date_of_month.index, by_date_of_month.values, marker='o', color='b') 
        plt.title('Number of Transactions based on Date of the Month')
        plt.xlabel('Date')
        plt.ylabel('Number of Purchases')
        plt.xticks(rotation=45)
        plt.grid()

        st.pyplot(fig)


st.header('Payment Type Usage')
col1, col2 = st.columns(2)

with col1:
    with st.container():
        fig, ax = plt.subplots(figsize=(10, 7))
        plt.pie(by_payment_type['order_id'], labels=by_payment_type['payment_type'], autopct='%1.1f%%', textprops={'fontsize': 8})
        plt.title('Proportion of Payment Type Usage')
        plt.tight_layout()

        st.pyplot(fig)

with col2:
    with st.container():
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x=by_payment_type['payment_type'], y=by_payment_type['payment_value'], palette='viridis')

        plt.xticks(rotation=90)
        plt.xlabel('Payment Type')
        plt.ylabel('Average Value of Payment')
        plt.title('Average Payment by Payment Types')
        st.pyplot(fig)

st.header('Review Keywords by Score')
tab_score1, tab_score2, tab_score3, tab_score4, tab_score5 = st.tabs(["Score 1", "Score 2", "Score 3", "Score 4", "Score 5"])

with tab_score1:
    with st.container():
        fig, ax = plt.subplots(figsize=(10, 7))

        text = ' '.join(by_score_1.dropna()) 
        
        wordcloud = WordCloud(width=800, height=400, background_color='white', max_words=100).generate(text)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off') 
        plt.title('Review Score: 1', fontsize=16)
        st.pyplot(fig)

with tab_score2:
    with st.container():
        fig, ax = plt.subplots(figsize=(10, 7))

        text = ' '.join(by_score_2.dropna()) 
        
        wordcloud = WordCloud(width=800, height=400, background_color='white', max_words=100).generate(text)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off') 
        plt.title('Review Score: 2', fontsize=16)
        st.pyplot(fig)


with tab_score3:
    with st.container():
        fig, ax = plt.subplots(figsize=(10, 7))

        text = ' '.join(by_score_3.dropna()) 
        
        wordcloud = WordCloud(width=800, height=400, background_color='white', max_words=100).generate(text)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off') 
        plt.title('Review Score: 3', fontsize=16)
        st.pyplot(fig)

with tab_score4:
    with st.container():
        fig, ax = plt.subplots(figsize=(10, 7))

        text = ' '.join(by_score_4.dropna()) 
        
        wordcloud = WordCloud(width=800, height=400, background_color='white', max_words=100).generate(text)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off') 
        plt.title('Review Score: 4', fontsize=16)
        st.pyplot(fig)
with tab_score5:
    with st.container():
        fig, ax = plt.subplots(figsize=(10, 7))

        text = ' '.join(by_score_5.dropna()) 
        
        wordcloud = WordCloud(width=800, height=400, background_color='white', max_words=100).generate(text)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off') 
        plt.title('Review Score: 5', fontsize=16)
        st.pyplot(fig)

