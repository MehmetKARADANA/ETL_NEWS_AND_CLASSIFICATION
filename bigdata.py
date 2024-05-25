# -*- coding: utf-8 -*-
"""BigData.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1dhubEcpsdaC37dGgEmjCc2XdH4h5OMlw
"""

!hostname -I

#gives ip address
!curl ipecho.net/plain

#Gives ip addresses with port numbers
!sudo lsof -i -P -n | grep LISTEN

!pip install confluent_kafka

from confluent_kafka import Producer
import requests

def delivery_report(err, msg):
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

def fetch_data_and_send_to_kafka(url):
    # Confluent Kafka Producer ayarları
    producer_conf = {
        'bootstrap.servers': 'pkc-12576z.us-west2.gcp.confluent.cloud:9092',
        'security.protocol': 'SASL_SSL',
        'sasl.mechanism': 'PLAIN',
        'sasl.username': 'KBET22XVE7ORVE46',
        'sasl.password': 'YUzpQqFx92/zZ10TlNbAK7RR1Zgo61xs6++GGornSuisj0dWspqAIcPr8DsUFquV'
    }

    # Producer oluşturma
    producer = Producer(producer_conf)
    topic = 'Mehmet'

    # URL'den veri çekme
    response = requests.get(url)
    if response.status_code == 200:
        data = response.text
        # URL'yi key olarak kullanarak veriyi Kafka'ya gönderme
        producer.produce(topic, key=url.encode('utf-8'), value=data.encode('utf-8'), callback=delivery_report)
        producer.flush()
        print("Success: Data sent to Kafka")
    else:
        print(f"Error: Failed to fetch data from URL. Status code: {response.status_code}")

if __name__ == "__main__":
    url = input("Enter URL: ")
    fetch_data_and_send_to_kafka(url)

!pip install confluent_kafka pymongo
!pip install pymongo

from confluent_kafka import Consumer, KafkaException, KafkaError
from pymongo import MongoClient

def insert_data_to_mongo(url, data, collection):
    result = collection.insert_one({"url": url, "data": data, "state": 0,"category":None})
    if result.inserted_id:
        print(f"Data inserted with ID: {result.inserted_id}")
    else:
        print("Failed to insert data")

def kafka_consumer_example():
    # Confluent Kafka Consumer ayarları
    consumer_conf = {
        'bootstrap.servers': 'pkc-12576z.us-west2.gcp.confluent.cloud:9092',
        'security.protocol': 'SASL_SSL',
        'sasl.mechanism': 'PLAIN',
        'sasl.username': 'KBET22XVE7ORVE46',
        'sasl.password': 'YUzpQqFx92/zZ10TlNbAK7RR1Zgo61xs6++GGornSuisj0dWspqAIcPr8DsUFquV',
        'group.id': 'my_group',
        'auto.offset.reset': 'earliest'
    }

    # Consumer oluşturma
    consumer = Consumer(consumer_conf)
    topic = 'Mehmet'
    consumer.subscribe([topic])

    # MongoDB bağlantısını oluşturma
    client = MongoClient("mongodb+srv://mehmet34:mehmet175e@atlascluster.j3z8vqq.mongodb.net/")
    db = client['mydatabase']
    collection = db['mycollection61']

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"End of partition reached {msg.topic()}/{msg.partition()}")
                else:
                    raise KafkaException(msg.error())
            else:
                url = msg.key().decode('utf-8') if msg.key() is not None else None
                data = msg.value().decode('utf-8')
                insert_data_to_mongo(url, data, collection)
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up
        consumer.close()

if __name__ == "__main__":
    kafka_consumer_example()

!pip install pymongo
!pip install certifi
!pip install pyspark
!pip install bs4

from pyspark.sql import SparkSession
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import certifi
from bs4 import BeautifulSoup
from bson import ObjectId

# SparkSession oluştur
spark = SparkSession.builder \
    .appName("MongoDB to Spark") \
    .config("spark.mongodb.input.uri", "mongodb+srv://mehmet34:mehmet175e@atlascluster.j3z8vqq.mongodb.net/mydatabase.mycollection61?authSource=admin") \
    .config("spark.mongodb.output.uri", "mongodb+srv://mehmet34:mehmet175e@atlascluster.j3z8vqq.mongodb.net/mydatabase.mycollection61?authSource=admin") \
    .getOrCreate()

def process_document(document):
    text = document['data']
    soup = BeautifulSoup(text, 'html.parser')

    for tag in soup.find_all(["a", "img", "strong"]):
        tag.decompose()

    articles = soup.find_all("article")
    if not articles:
        warning_message = f"Uyarı: {document['url']} adresinde article etiketi bulunamadı."
        return (document['_id'], warning_message, None, 0)

    combined_text = ""
    for article in articles:
        paragraphs = article.find_all(["p", "h1", "h2"])
        combined_text = " ".join(element.get_text() for element in paragraphs)

    return (document['_id'], document['url'], combined_text, 1)

# MongoDB'ye bağlan ve verileri çek
try:
    client = MongoClient(
        "mongodb+srv://mehmet34:mehmet175e@atlascluster.j3z8vqq.mongodb.net/",
        tlsCAFile=certifi.where()
    )
    db = client["mydatabase"]
    collection = db["mycollection61"]

    # İşlenmemiş verileri al
    documents = list(collection.find({"data": {"$exists": True}, "state": 0}))

    # İşlenmemiş veri yoksa mesaj ver
    if not documents:
        print("İşlenmemiş veri yok.")
    else:
        # Belgeleri basit Python veri türlerine dönüştür
        simplified_documents = []
        for document in documents:
            simplified_document = {
                "_id": str(document["_id"]),
                "url": document["url"],
                "data": document["data"],
                "state": document["state"]
            }
            simplified_documents.append(simplified_document)

        # Spark DataFrame oluştur
        rdd = spark.sparkContext.parallelize(simplified_documents)
        df = spark.createDataFrame(rdd)

        # UDF ile işlemi Spark üzerinde dağıtık olarak gerçekleştir
        processed_rdd = df.rdd.map(lambda row: process_document(row.asDict()))
        processed_df = processed_rdd.toDF(["_id", "url", "data", "state"])

        # İşlenmiş verileri MongoDB'ye yaz
        processed_documents = processed_df.collect()
        for doc in processed_documents:
            query = {"_id": ObjectId(doc['_id'])}  # String olarak saklanan ObjectId'yi geri dönüştür
            new_data = {"$set": {"data": doc['data'], "state": 1}}
            try:
                collection.update_one(query, new_data)
                print(f"Veri başarıyla ayrıştırıldı: {doc['url']}")
                print(f"Ayrıştırılmış veri: {doc['data']}")
            except Exception as e:
                print(f"Veri güncellenirken hata oluştu: {e}")

except ServerSelectionTimeoutError as err:
    print("MongoDB bağlantı hatası:", err)

!pip install pandas
!pip install numpy
!pip install pandas xlrd
!pip install gspread pandas gspread_dataframe

from google.colab import files

# Dosya yükleme arayüzünü açın
uploaded = files.upload()

# Yüklenen dosyaları pandas ile okuyun
import pandas as pd

# Dosya adını belirleyin
file_name = list(uploaded.keys())[0]

import pandas as pd
from pymongo import MongoClient
import certifi
import bs4
import numpy as np


# Dosyayı okuyun
veri = pd.read_excel(file_name, engine='xlrd')

veri = veri[~veri['category'].isin(['dünya', 'genel','güncel','planet','türkiye'])]
bos_degerler = veri['content'].isnull() | veri['content'].str.strip().eq('')
veri = veri[~bos_degerler]

#'Content' ve 'Headline' sütunlarını birleştir
veri['content_headline'] = veri['content'].astype(str) + " " + veri['headline'].astype(str)


# Özellikler ve etiketler
X = veri['content_headline']
y = veri['category']


from sklearn.preprocessing import LabelEncoder

# LabelEncoder oluştur
label_encoder = LabelEncoder()

# y'yi sayısal değerlere dönüştür
y = label_encoder.fit_transform(y)

# y'nin boyutlarını ve örneklerini kontrol edelim
print(y.shape)
print(y[:10])
print("--"*10)

from sklearn.feature_extraction.text import TfidfVectorizer

# TF-IDF vektörizeri kullanarak metin verisini sayısallaştırma
tfidf_vectorizer = TfidfVectorizer()
X = tfidf_vectorizer.fit_transform(X)

# X'in boyutlarını kontrol edelim
print(X.shape)
print("--"*10)

from sklearn.model_selection import train_test_split

# Veri setlerini ayır
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Ayrılan setlerin boyutlarını kontrol edelim
print(X_train.shape, X_test.shape)
print(y_train.shape, y_test.shape)

from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score


# Farklı k değerlerini deneyelim
k_values = [3, 5, 7, 9]

for k in k_values:
    knn_model = KNeighborsClassifier(n_neighbors=k)
    knn_model.fit(X_train, y_train)
    y_pred = knn_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"k={k} için test seti doğruluk oranı: {accuracy}")


try:
    client = MongoClient(
        "mongodb+srv://mehmet34:mehmet175e@atlascluster.j3z8vqq.mongodb.net/",
        tlsCAFile=certifi.where()
    )
    db = client["mydatabase"]
    collection = db["mycollection61"]


    documents = collection.find({"data": {"$exists": True}, "category": None,"state":1})


    if collection.count_documents({"data": {"$exists": True}, "state": 1,"category":None}) == 0:
        print("Kategorize edilmemiş veri yok.")
    else:
        for document in documents:
            text = document['data']

            girdi_metni = text
            girdi_vetörü = tfidf_vectorizer.transform([girdi_metni])  # TF-IDF vektörizasyonu ile dönüştürme

      # Model tahmini
            tahmin = knn_model.predict(girdi_vetörü)

       # Tahmin sonucunu kategorik etikete dönüştürme
            tahmin_kategori = label_encoder.inverse_transform(tahmin)

        # Sonucu yazdırma
            print("Girdi Metni:", girdi_metni)
            print("Tahmin Edilen Kategori:", tahmin_kategori)
            numpy_dizi = np.array(tahmin_kategori, dtype=object)
           # Numpy dizisinin metin içeriğini al
            category = numpy_dizi[0]
            query = {"_id": document["_id"]}
            new_category = {"$set": {"category":category}}

            try:
                collection.update_one(query, new_category)
                print("Veri Başarı İle Sınıflandırıldı.")
            except Exception as e:
                print(e)

            print("#########")
except Exception as e:
    print(f"Bir hata oluştu: {e}")

finally:
    client.close()
    print("MongoDB bağlantısı kapatıldı.")

!pip install pyspark

from pyspark.sql import SparkSession
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import certifi
import pandas as pd

try:
    # MongoDB bağlantısı
    client = MongoClient(
        "mongodb+srv://mehmet34:mehmet175e@atlascluster.j3z8vqq.mongodb.net/",
        tlsCAFile=certifi.where()
    )
    db = client["mydatabase"]
    collection = db["mycollection61"]

    # MongoDB verisini çekme
    mongo_data = list(collection.find({"state": 1, "category": {"$ne": None}}, {"url": 1, "data": 1, "category": 1, "_id": 0}))

    # SparkSession oluşturma
    spark = SparkSession.builder \
        .appName("Spark DataFrame") \
        .getOrCreate()

    # Pandas DataFrame oluşturma
    pdf = pd.DataFrame(mongo_data)

    # Pandas DataFrame'i Spark DataFrame'e dönüştürme
    df = spark.createDataFrame(pdf)

    # DataFrame'i gösterme
    df.show()

    #aynı tablo
    # DataFrame'i SQL tablosu olarak kullanmak için bir geçici tablo oluşturma
   # df.createOrReplaceTempView("mongo_table")
    #result = spark.sql("SELECT * FROM mongo_table WHERE category IS NOT NULL")
    #result.show()



except ServerSelectionTimeoutError as err:
    print("MongoDB bağlantı hatası:", err)
except Exception as e:
    print(f"Bir Hata Oluştu: {e}")
finally:
    spark.stop()
    client.close()
    print("MongoDB bağlantısı kapatıldı.")