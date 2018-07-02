# -*- coding: utf-8 -*-
"""
Created on Fri Apr 20 20:06:55 2018

@author: ravi_
"""
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import googlemaps
gmaps = googlemaps.Client(key='AIzaSyABkTFemTNy1ct-tx0wMh-41MpZw3btKlU')
import datetime
from dateutil.relativedelta import relativedelta
import datedelta

from sklearn import linear_model
from sklearn.model_selection import ShuffleSplit
from sklearn.model_selection import cross_val_score

from sklearn.metrics import mean_squared_error
from math import sqrt


epoch = datetime.datetime.utcfromtimestamp(0)
def unix_time_millis(dt):
    return (dt - epoch).total_seconds() 

df = pd.read_csv('train.csv')
df.pickup_datetime=datetime.date(df.pickup_datetime)
#new pickuptime for future dates keeping weekdays constant
df.pickup_datetime_new = df.pickup_datetime + datetime.timedelta(days=1099)
df.pickup_datetime_new = df.pickup_datetime_new + datetime.timedelta(minutes = 240)

df.epoch = df.pickup_datetime_new.apply(lambda x: unix_time_millis(x))
columns = ['Predicted', 'Actual']
index = range(1, 99)
driving_time = pd.DataFrame(columns=columns, index = index)

import urllib.request, json
for i in range(1, 99):
#Google MapsDdirections API endpoint
    endpoint = 'https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&'
    api_key = 'AIzaSyABkTFemTNy1ct-tx0wMh-41MpZw3btKlU'
    orig_coord = str(df.pickup_latitude[i]) + ',' + str(df.pickup_longitude[i])

    dest_coord = str(df.dropoff_latitude[i]) +',' + str(df.dropoff_longitude[i])
    departure_time = int(df.epoch[i])
    nav_request = 'origins={}&destinations={}&departure_time={}&traffic_model=best_guess&key={}'.format(orig_coord, dest_coord, departure_time, api_key)
    request = endpoint + nav_request

#Sends the request and reads the response.
    try:
        response = urllib.request.urlopen(request).read()
    except urllib.error.HTTPError as err:
        print(err.code)
    
#Loads response as JSON
    directions = json.loads(response)
    

    #print(directions)
    predicted_time = directions['rows'][0]['elements'][0]['duration_in_traffic']['value']
    driving_time.Predicted[i] = predicted_time
    driving_time.Actual[i] = df.trip_duration[i]
    print(predicted_time,  df.trip_duration[i])



regr = linear_model.LinearRegression()
x = driving_time.Predicted.reshape(98, 1)
y = driving_time.Actual.reshape(98, 1)


regr.fit(x, y)
regr.score(x, y)

#output - 62.36
df['pu_hour'] = df.pickup_datetime.dt.hour
df['yday'] = df.pickup_datetime.dt.dayofyear
df['wday'] = df.pickup_datetime.dt.dayofweek
df['new date'] = df['pickup_datetime'].dt.second()
df.head()

wdf = pd.read_csv('weather_data_nyc_centralpark_2016(1).csv')
wdf['date']=pd.to_datetime(wdf.date,format='%d-%m-%Y')
wdf['yday'] = wdf.date.dt.dayofyear

wdf.head()
falls = [ 0.01 if c=='T' else float(c) for c in wdf['snow fall']]
rain = [ 0.01 if c=='T' else float(c) for c in wdf['precipitation']]
wdf['snow fall']= falls
wdf['precipitation'] = rain

df = pd.merge(df,wdf,on='yday')
df.head()

#df = df.drop(['date','maximum temerature','minimum temperature'],axis=1)
df.head()

import seaborn as sns
import matplotlib.pyplot as plt
plt.subplots(1,1,figsize=(17,15))
rain = wdf['precipitation']
sns.barplot(wdf['yday'], rain)

intensity = wdf['precipitation'].apply(lambda x:'L' if x < 0.098 
                           else 'M' if x>=0.098 and x<0.30 
                           else 'H' if x>=0.30 and x<2.0
                           else 'V')
wdf['precipitation'] = intensity
rain_count = wdf['precipitation'].value_counts().sort_values()
plt.subplots(1,1,figsize=(17,10))
sns.barplot(rain_count.index,rain_count.values)

day =1
df_day=df[((df.pickup_datetime<'2016-02-'+str(day+1))&
           (df.pickup_datetime>='2016-02-'+str(day)))]

import matplotlib.pyplot as plt
fig, ax = plt.subplots(ncols=1, nrows=1,figsize=(12,10))
plt.ylim(40.6, 40.9)
plt.xlim(-74.1,-73.7)
ax.scatter(df['pickup_longitude'],df['pickup_latitude'], s=0.0002, alpha=1)

#plt.figure(figsize=(8,6))
f,axarr = plt.subplots(ncols=2,nrows=1,figsize=(12,6))
axarr[0].scatter(range(df.shape[0]), np.sort(df.trip_duration.values))
q = df.trip_duration.quantile(0.99)
df = df[df.trip_duration < q]
axarr[1].scatter(range(df.shape[0]), np.sort(df.trip_duration.values))

plt.show()

def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)

    All args must be of equal length.    

    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2

    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km
df['distance'] = haversine_np(df.pickup_longitude, df.pickup_latitude,
                                           df.dropoff_longitude, df.dropoff_latitude)

import seaborn as sns
#sns.set(style="ticks")
sel = df[['distance','passenger_count']]
sns.barplot(x='passenger_count',y='distance',data=sel)
#sns.despine(offset=10, trim=True)

import seaborn as sns
#sns.set(style="ticks")
sel = df[['distance','wday']]
sns.barplot(x='wday',y='distance',data=sel)
#sns.despine(offset=10, trim=True)

#Attempting Regression
features = df[['wday','yday','pu_hour','passenger_count','pickup_latitude','pickup_longitude','vendor_id']]
target = df[['trip_duration']]



reg = linear_model.LinearRegression()
cv = ShuffleSplit(n_splits=4, test_size=0.3, random_state=0)
cross_val_score(reg, features, target, cv=cv)
#reg.fit (features, target)

reg = linear_model.Ridge (alpha = .5)
cv = ShuffleSplit(n_splits=4, test_size=0.3, random_state=0)
cross_val_score(reg, features, target, cv=cv)

reg.fit(features,target)


tdf = pd.read_csv('test.csv')
tdf.pickup_datetime=pd.to_datetime(tdf.pickup_datetime)
#tdf.dropoff_datetime=pd.to_datetime(tdf.dropoff_datetime)
tdf['pu_hour'] = tdf.pickup_datetime.dt.hour
tdf['yday'] = tdf.pickup_datetime.dt.dayofyear
tdf['wday'] = tdf.pickup_datetime.dt.dayofweek

tfeatures = tdf[['wday','yday','pu_hour','passenger_count','pickup_latitude','pickup_longitude','vendor_id']]
pred = reg.predict(tfeatures)

tdf['trip_duration']=pred.astype(int)
out = tdf[['id','trip_duration']]

out['trip_duration'].isnull().values.any()
out.to_csv('pred_linear_1.csv',index=False)

from sklearn.cluster import KMeans
import numpy as np
import pickle

try:
    kmeans = pickle.load(open("source_kmeans.pickle", "rb"))
except:
    kmeans = KMeans(n_clusters=20, random_state=0).fit(df[['pickup_longitude','pickup_latitude']])
    pickle.dump(kmeans, open('source_kmeans.pickle', 'wb'))


cx = [c[0] for c in kmeans.cluster_centers_]
cy = [c[1] for c in kmeans.cluster_centers_]

fig, ax = plt.subplots(ncols=1, nrows=1,figsize=(12,10))
plt.ylim(40.6, 40.9)
plt.xlim(-74.1,-73.7)

df['cluster'] = kmeans.predict(df[['pickup_longitude','pickup_latitude']])
cm = plt.get_cmap('gist_rainbow')

colors = [cm(2.*i/15) for i in range(20)]
colored = [colors[k] for k in df['cluster']]

#plt.figure(figsize = (10,10))
ax.scatter(df.pickup_longitude,df.pickup_latitude,color=colored,s=0.0002,alpha=1)
ax.scatter(cx,cy,color='Black',s=50,alpha=1)
plt.title('Taxi Pickup Clusters')
plt.show()
plt.ylim(40.6, 40.9)

fig, ax = plt.subplots(ncols=1, nrows=1,figsize=(12,10))
plt.ylim(40.6, 40.9)
plt.xlim(-74.1,-73.7)


colors = [cm(2.*i/15) for i in range(20)]
colored = [colors[k] for k in df['dest_cluster']]

ax.scatter(df.dropoff_longitude,df.dropoff_latitude,color=colored,s=0.0002,alpha=1)
ax.scatter(cx,cy,color='Black',s=50,alpha=1)
plt.title('Taxi Dropoff Clusters')
plt.show()

from sklearn.cluster import KMeans
import numpy as np
import pickle

try:
    kmeans = pickle.load(open("source_kmeans.pickle", "rb"))
except:
    kmeans = KMeans(n_clusters=20, random_state=0).fit(df[['pickup_longitude','pickup_latitude']])
    pickle.dump(kmeans, open('source_kmeans.pickle', 'wb'))


cx = [c[0] for c in kmeans.cluster_centers_]
cy = [c[1] for c in kmeans.cluster_centers_]

tdf['cluster'] = kmeans.predict(tdf[['pickup_longitude','pickup_latitude']])


