# -*- coding: utf-8 -*-
"""Final code.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1dyM7eNRLmZsGSBP37EvmJESZIdqV7ylp
"""

#Import library
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import twitter
import nltk
import re
from nltk.sentiment.vader import SentimentIntensityAnalyzer
nltk.download('vader_lexicon')
from textblob import TextBlob
import string
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.decomposition import NMF
import pyLDAvis.sklearn
import networkx as nx
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import spacy
import gensim
from sklearn.model_selection import GridSearchCV
from wordcloud import STOPWORDS

#import twitter key
CONSUMER_KEY = 'IZQ8CyodPG2rNJBLNJbuMWD6y'
CONSUMER_SECRET = 'H8kAZFZ9UlqNOZcMQ4PDvKrg5NIQrTlrK3aU3hWQ3hgT9Obh0C'
OAUTH_TOKEN = '1388067604007370753-R5hHaiG9CW84jpMCTdKeWZwHp9XuUv'
OAUTH_TOKEN_SECRET = 'UvRhAcUt6mWx3W9FxEZ0bahZIhCnTx5HDl3ZTYAfQ1qmS'

#-- login to Twitter with all your authorization details
auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET)

#-- Create a Twitter 'object' that we will be able to query in your code
twitter_api = twitter.Twitter(auth=auth)

!pip install -U pip setuptools wheel
!pip install -U spacy
!python -m spacy download en_core_web_sm

"""## DATA EXPLORATION

Merging - As the collection includes several data batches
"""

#If testing please ignore this cell
#Load the first file
mcu=pd.read_csv('1.csv')
dc=pd.read_csv('DC1.csv')

#If testing please ignore this cell
#Merging MCU
for i in range(2,20):
    temp=pd.read_csv(str(i)+'.csv')
    mcu=pd.concat([mcu,temp],axis=0,ignore_index=True)
    
#Merging DC
for i in range(2,16):
    temp=pd.read_csv('DC'+str(i)+'.csv')
    dc=pd.concat([dc,temp],axis=0,ignore_index=True)

#If testing run this cell for small batch of data
mcu=pd.read_csv('3.csv')
dc=pd.read_csv('DC3.csv')

"""Data processing"""

#Drop duplicated
mcu.drop_duplicates(subset='id',inplace=True)

#Drop duplicated
dc.drop_duplicates(subset='id',inplace=True)

# % of null value
# - It can be seen that most values of geography missing => exlude from analysis
# - Columns that have similar missing values and will be use for analysis includes: 
# created_at, id, text, in_reply, user, lang, extended_tweet, retweeted_status
mcu.isnull().mean()*100

#clean the data where user is NA
mcu_clean=mcu[mcu.user.isna()==False]
dc_clean=dc[dc.user.isna()==False]

#converting time
mcu_clean=mcu_clean.astype({'created_at': 'datetime64'})
dc_clean=dc_clean.astype({'created_at': 'datetime64'})

#checking record time
print(f" MCU Data Available since {mcu_clean.created_at.min()}")
print(f" MCU Data Available upto {mcu_clean.created_at.max()}")
print(f" DC Data Available since {dc_clean.created_at.min()}")
print(f" DC Data Available upto {dc_clean.created_at.max()}")

#as collecting code run in different time - slide data to take same period for MCU and DCEU
mcu_clean=mcu_clean[(mcu_clean.created_at>='2021-05-10 17:35:41') & (mcu_clean.created_at<='2021-05-17 07:14:24')]

#reset index
mcu_clean=mcu_clean.reset_index()
dc_clean=dc_clean.reset_index()
mcu_clean.head()

#drop index
mcu_clean.drop(columns=['index','Unnamed: 0'])
dc_clean.drop(columns=['index','Unnamed: 0'])

#checking key stats
pd.set_option('display.max_columns',None)
mcu_clean.describe(include='all')

#Taking relevant columns
mcu_short=mcu_clean[['id','created_at','text','in_reply_to_status_id',
                     'in_reply_to_user_id','in_reply_to_screen_name',
                     'user', 'retweeted_status', 'lang', 'extended_tweet']]
dc_short=dc_clean[['id', 'created_at','text','in_reply_to_status_id',
                     'in_reply_to_user_id','in_reply_to_screen_name',
                     'user', 'retweeted_status', 'lang', 'extended_tweet']]

"""Unpack user column
Taking: user_id, user_name, user_follower, user_following, user_verified, user_status, user_created
Unpack retweet column
Taking: id of original tweet, user id of original tweet
"""

#Convert user column to dictionary
import re
mcu_short['user_dict']=['']*len(mcu_short)
for i in range(len(mcu_short)):
    mcu_short['user_dict'][i]=eval(re.search(r"{.+}", mcu_short['user'][i]).group(0))

dc_short['user_dict']=['']*len(dc_short)
for i in range(len(dc_short)):
    dc_short['user_dict'][i]=eval(re.search(r"{.+}", dc_short['user'][i]).group(0))
    
#Convert retweet column to dictionary
mcu_short['retweet_dict']=['']*len(mcu_short)
for i in range(len(mcu_short)):
    try:
        mcu_short['retweet_dict'][i]=eval(re.search(r"{.+}", mcu_short['retweeted_status'][i]).group(0))
    except TypeError:
        pass
    
dc_short['retweet_dict']=['']*len(dc_short)
for i in range(len(dc_short)):
    try:
        dc_short['retweet_dict'][i]=eval(re.search(r"{.+}", dc_short['retweeted_status'][i]).group(0))
    except TypeError:
        pass
    
#Convert retweet_user column to dictionary
mcu_short['retweet_user_dict']=['']*len(mcu_short)
for i in range(len(mcu_short)):
    try:
        mcu_short['retweet_user_dict'][i]=eval(re.search(r"{.+}", mcu_short['retweeted_status'][i]).group(0))['user']
    except TypeError:
        pass
    
dc_short['retweet_user_dict']=['']*len(dc_short)
for i in range(len(dc_short)):
    try:
        dc_short['retweet_user_dict'][i]=eval(re.search(r"{.+}", dc_short['retweeted_status'][i]).group(0))['user']
    except TypeError:
        pass

#Break down dictionary elements - function
def dict_break(data, dictionary, new_col, old_col, integer):
    if integer=='integer':
        data[new_col]=['']*len(data)
        for i in range(len(data)):
            try:
                data[new_col][i]=int(data[dictionary][i][old_col])
            except TypeError:
                pass
    else:
        data[new_col]=['']*len(data)
        for i in range(len(data)):
            try:
                data[new_col][i]=data[dictionary][i][old_col]
            except TypeError:
                pass

#MCU
#User dictionary
dict_break(mcu_short,'user_dict','user_id','id','integer')
dict_break(mcu_short,'user_dict','user_name','screen_name','string')
dict_break(mcu_short,'user_dict','user_location','location','string')
dict_break(mcu_short,'user_dict','user_created','created_at','string')
dict_break(mcu_short,'user_dict','user_verified','verified','string')
dict_break(mcu_short,'user_dict','user_follower','followers_count','integer')
dict_break(mcu_short,'user_dict','user_following','friends_count','integer')
dict_break(mcu_short,'user_dict','user_like','favourites_count','integer')
dict_break(mcu_short,'user_dict','user_status','statuses_count','integer')
#Retweet dictionary
dict_break(mcu_short,'retweet_dict','in_retweet_to_status_id','id','integer')
#Retweet user dictionary
dict_break(mcu_short,'retweet_user_dict','in_retweet_to_user_id','id','integer')

#DC
#User dictionary
dict_break(dc_short,'user_dict','user_id','id','integer')
dict_break(dc_short,'user_dict','user_name','screen_name','string')
dict_break(dc_short,'user_dict','user_location','location','string')
dict_break(dc_short,'user_dict','user_created','created_at','string')
dict_break(dc_short,'user_dict','user_verified','verified','string')
dict_break(dc_short,'user_dict','user_follower','followers_count','integer')
dict_break(dc_short,'user_dict','user_following','friends_count','integer')
dict_break(dc_short,'user_dict','user_like','favourites_count','integer')
dict_break(dc_short,'user_dict','user_status','statuses_count','integer')
#Retweet dictionary
dict_break(dc_short,'retweet_dict','in_retweet_to_status_id','id','integer')
#Retweet user dictionary
dict_break(dc_short,'retweet_user_dict','in_retweet_to_user_id','id','integer')

#recheck NA
mcu_short.isnull().mean()*100

#checking on location again - not standardised => remove
mcu_short.user_location.value_counts()

mcu_short.drop(columns='user_location')
dc_short.drop(columns='user_location')

"""Merging truncated tweet with extended tweet"""

# merging text with full text
#MCU
import re
mcu_short['full_text']=['']*len(mcu_short)
for i in range(len(mcu_short)):
    try: 
        if mcu_short['extended_tweet'][i] is np.nan:
            mcu_short['full_text'][i]=mcu_short['text'][i]
        else:
            mcu_short['full_text'][i]=eval(re.search(r"{.+}", mcu_short['extended_tweet'][i]).group(0))['full_text']
    except TypeError:
        continue

# merging text with full text
#DC
import re
dc_short['full_text']=['']*len(dc_short)
for i in range(len(dc_short)):
    try: 
        if dc_short['extended_tweet'][i] is np.nan:
            dc_short['full_text'][i]=dc_short['text'][i]
        else:
            dc_short['full_text'][i]=eval(re.search(r"{.+}", dc_short['extended_tweet'][i]).group(0))['full_text']
    except TypeError:
        continue

#Saving the data as the cleaning task processing task very expensive
mcu_short.to_csv('mcu_short.csv')
dc_short.to_csv('dc_short.csv')

#Reload data
mcu_short=pd.read_csv('mcu_short.csv')
dc_short=pd.read_csv('dc_short.csv')

mcu_short.describe(include='all')

dc_short.describe(include='all')

#Create new column 'network' with retweet and reply original user id
#MCU
mcu_short['network']=['']*len(mcu_short)
for i in range(len(mcu_short)):
    if mcu_short['in_reply_to_user_id'].isnull()[i]==True:
        mcu_short['network'][i]=mcu_short['in_retweet_to_user_id'][i]
    else:
        mcu_short['network'][i]=mcu_short['in_reply_to_user_id'][i]

#Create new column 'network' with retweet and reply original user id
#DC
dc_short['network']=['']*len(dc_short)
for i in range(len(dc_short)):
    if dc_short['in_reply_to_user_id'].isnull()[i]==True:
        dc_short['network'][i]=dc_short['in_retweet_to_user_id'][i]
    else:
        dc_short['network'][i]=dc_short['in_reply_to_user_id'][i]

#Check unique users of 2 fanbase
print(mcu_short.user_id.nunique())
print(dc_short.user_id.nunique())

#Final columns to be used
mcu_short=mcu_short[['id','created_at',
                     'in_reply_to_status_id','in_reply_to_user_id',
                     'lang','user_id','user_name',
                     'in_retweet_to_status_id','in_retweet_to_user_id',
                     'full_text','network']]
dc_short=dc_short[['id','created_at',
                     'in_reply_to_status_id','in_reply_to_user_id',
                     'lang','user_id','user_name',
                     'in_retweet_to_status_id','in_retweet_to_user_id',
                     'full_text','network']]

"""## Key stats"""

mcu_short.head()

#Tweet per account MCU
len(mcu_short)/mcu_short.user_id.nunique()

#Tweet per account DC
len(dc_short)/dc_short.user_id.nunique()

#Dynamic & spread out of tweet

#MCU
print('MCU')
# % of original post - where the tweet is not reply or retweet
print ('orginal:',len(mcu_short[mcu_short.network.isnull()==True])/len(mcu_short))
# % of reply
print ('reply:', len(mcu_short[mcu_short.in_reply_to_user_id.isnull()==False])/len(mcu_short))
# % of retweet
print ('retweet:', len(mcu_short[mcu_short.in_retweet_to_user_id.isnull()==False])/len(mcu_short))

#DC
print('DC')
# % of original post - where the tweet is not reply or retweet
print ('orginal:',len(dc_short[dc_short.network.isnull()==True])/len(dc_short))
# % of reply
print ('reply:', len(dc_short[dc_short.in_reply_to_user_id.isnull()==False])/len(dc_short))
# % of retweet
print ('retweet:', len(dc_short[dc_short.in_retweet_to_user_id.isnull()==False])/len(dc_short))

#most retweet - MCU
print(mcu_short.in_retweet_to_status_id.value_counts().head(1).values)
mcu_clean[mcu_clean.id==mcu_short.in_retweet_to_status_id.value_counts().head(1).index[0]].text.values

#most reply - MCU
print(mcu_short.in_reply_to_status_id.value_counts().head(1).values)
mcu_clean[mcu_clean.id==mcu_short.in_reply_to_status_id.value_counts().head(1).index[0]].text.values

#most retweet - DC
print(dc_short.in_retweet_to_status_id.value_counts().head(1).values)
dc_clean[dc_clean.id==dc_short.in_retweet_to_status_id.value_counts().head(1).index[0]].text.values

#most reply - DC
print(dc_short.in_reply_to_status_id.value_counts().head(1).values)
dc_clean[dc_clean.in_reply_to_status_id==dc_short.in_reply_to_status_id.value_counts().head(1).index[0]].head(4)

#lets explore created_at column
cnt_srs = mcu_short['created_at'].dt.date.value_counts()
cnt_srs = cnt_srs.sort_index()
plt.figure(figsize=(14,6))
sns.barplot(cnt_srs.index, cnt_srs.values, alpha=0.8, color='red')
plt.xticks(rotation='vertical')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Number of tweets', fontsize=12)
plt.title("MCU - Number of tweets according to dates")
plt.show()

#lets explore created_at column
cnt_srs = dc_short['created_at'].dt.date.value_counts()
cnt_srs = cnt_srs.sort_index()
plt.figure(figsize=(14,6))
sns.barplot(cnt_srs.index, cnt_srs.values, alpha=0.8, color='deepskyblue')
plt.xticks(rotation='vertical')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Number of tweets', fontsize=12)
plt.title("DC - Number of tweets according to dates")
plt.show()

# Language absolute
# MCU
print(mcu_short.lang.value_counts().head(20))
plt.figure(figsize=(6,4))
sns.barplot(mcu_short.lang.value_counts().head(5).index, mcu_short.lang.value_counts().head(5).values, alpha=0.8, color='red')
plt.yticks(np.arange(0, 120000, step=20000))
plt.xlabel('Lang', fontsize=12)
plt.ylabel('Number of tweets', fontsize=12)
plt.title("MCU - Number of tweets according to language")

# Language precentage
# MCU
mcu_short.lang.value_counts()/len(mcu_short)

# Language absolute
# DC
print(dc_short.lang.value_counts().head(20))
plt.figure(figsize=(6,4))
sns.barplot(dc_short.lang.value_counts().head(5).index, dc_short.lang.value_counts().head(5).values, alpha=0.8, color='deepskyblue')
plt.yticks(np.arange(0, 120000, step=20000))
plt.xlabel('Lang', fontsize=12)
plt.ylabel('Number of tweets', fontsize=12)
plt.title("DC - Number of tweets according to language")

# Language percentage
# DC
dc_short.lang.value_counts()/len(dc_short)

"""## Sentiment Analysis """

# Taking English tweet
mcu_en=mcu_short[mcu_short.lang=='en']
dc_en=dc_short[dc_short.lang=='en']

# Sentiment MCU
for index, row in mcu_en['full_text'].iteritems():
    score = SentimentIntensityAnalyzer().polarity_scores(row)
    neg = score['neg']
    neu = score['neu']
    pos = score['pos']
    comp = score['compound']
    if neg > pos:
        mcu_en.loc[index, 'sentiment'] = 'negative'
    elif pos > neg:
        mcu_en.loc[index, 'sentiment'] = 'positive'
    else:
        mcu_en.loc[index, 'sentiment'] = 'neutral'
    mcu_en.loc[index, 'neg'] = neg
    mcu_en.loc[index, 'neu'] = neu
    mcu_en.loc[index, 'pos'] = pos
    mcu_en.loc[index, 'compound'] = comp
mcu_en.head(10)

#Sentiment DC
for index, row in dc_en['full_text'].iteritems():
    score = SentimentIntensityAnalyzer().polarity_scores(row)
    neg = score['neg']
    neu = score['neu']
    pos = score['pos']
    comp = score['compound']
    if neg > pos:
        dc_en.loc[index, 'sentiment'] = 'negative'
    elif pos > neg:
        dc_en.loc[index, 'sentiment'] = 'positive'
    else:
        dc_en.loc[index, 'sentiment'] = 'neutral'
    dc_en.loc[index, 'neg'] = neg
    dc_en.loc[index, 'neu'] = neu
    dc_en.loc[index, 'pos'] = pos
    dc_en.loc[index, 'compound'] = comp
dc_en.head(10)

#Count_values for sentiment
def count_values_in_column(data,feature):
    total=data.loc[:,feature].value_counts(dropna=False)
    percentage=round(data.loc[:,feature].value_counts(dropna=False,normalize=True)*100,2)
    return pd.concat([total,percentage],axis=1,keys=['Total','Percentage'])

#MCU sentiment
count_values_in_column(mcu_en,'sentiment')

#DC sentiment
count_values_in_column(dc_en,'sentiment')

"""## Topic modelling """

#clean RT, emoticon,hyperlink
import preprocessor.api as p
from preprocessor.api import clean, set_options
for i in mcu_en.full_text.index:
    mcu_en.full_text[i]=clean(mcu_en.full_text[i])
for i in dc_en.full_text.index:
    dc_en.full_text[i]=clean(dc_en.full_text[i])

#Tokenize function
def sent_to_words(sentences):
    for sentence in sentences:
        yield(gensim.utils.simple_preprocess(str(sentence), deacc=True))
        
#Lemmatize function
def lemmatization(texts, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV']):
    """https://spacy.io/api/annotation"""
    texts_out = []
    for sent in texts:
        doc = nlp(" ".join(sent)) 
        texts_out.append(" ".join([token.lemma_ if token.lemma_ not in ['-PRON-'] else '' for token in doc if token.pos_ in allowed_postags]))
    return texts_out

#Clean text - MCU
# Convert to list
mcu_en['clean_text'] = mcu_en.full_text.values.tolist()

# Remove Emails
mcu_en['clean_text'] = [re.sub('\S*@\S*\s?', '', sent) for sent in mcu_en['clean_text']]

# Remove new line characters
mcu_en['clean_text'] = [re.sub('\s+', ' ', sent) for sent in mcu_en['clean_text']]

# Remove distracting single quotes
mcu_en['clean_text'] = [re.sub("\'", "", sent) for sent in mcu_en['clean_text']]

#Tokenize
mcu_en['clean_text'] = list(sent_to_words(mcu_en['clean_text']))

#Lemmarize
nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
mcu_en['clean_text'] = lemmatization(mcu_en['clean_text'], allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])

print(mcu_en['clean_text'][:1])

#Clean text - DC
# Convert to list
dc_en['clean_text'] = dc_en.full_text.values.tolist()

# Remove Emails
dc_en['clean_text'] = [re.sub('\S*@\S*\s?', '', sent) for sent in dc_en['clean_text']]

# Remove new line characters
dc_en['clean_text'] = [re.sub('\s+', ' ', sent) for sent in dc_en['clean_text']]

# Remove distracting single quotes
dc_en['clean_text'] = [re.sub("\'", "", sent) for sent in dc_en['clean_text']]

#Tokenize
dc_en['clean_text'] = list(sent_to_words(dc_en['clean_text']))

#Lemmatize
nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
dc_en['clean_text'] = lemmatization(dc_en['clean_text'], allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])

print(dc_en['clean_text'][:1])

#use stopword list from wordcloud 
stopwords = list(STOPWORDS)
#append search term in stopwords
stopwords_mcu=stopwords+['mcu']
stopwords_dc=stopwords+['dceu']

"""## Topic modelling

MCU
"""

#Vectorizing
mcu_vectorizer = CountVectorizer(      
                             min_df=5, 
                             max_df=0.8,
                             stop_words=stopwords_mcu, # remove stop words
                             lowercase=True)      

mcu_vectorized = mcu_vectorizer.fit_transform(mcu_en.clean_text)

# GridSearch for LDA
# Define Search Param

search_params = {'n_components': range(5,15)}

# Init the Model
lda = LatentDirichletAllocation(random_state=42)

# Init Grid Search Class
model_mcu = GridSearchCV(lda, param_grid=search_params)

# Do the Grid Search
model_mcu.fit(mcu_vectorized)

model_mcu.cv_results_

# Store result
component_mcu={}
for i in range(10):
    component_mcu[str(i+5)]= [model_mcu.cv_results_['split0_test_score'][i]]
    component_mcu[str(i+5)].append(model_mcu.cv_results_['split1_test_score'][i])
    component_mcu[str(i+5)].append(model_mcu.cv_results_['split2_test_score'][i])
    component_mcu[str(i+5)].append(model_mcu.cv_results_['split3_test_score'][i])
    component_mcu[str(i+5)].append(model_mcu.cv_results_['split4_test_score'][i])

component_mcu=pd.DataFrame(component_mcu)

# plot result's distribution
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111)
medianprops = dict(linestyle='-', linewidth=2.5, color='orangered')
plt.boxplot(component_mcu, medianprops = medianprops)
ax.set_xticklabels(component_mcu.columns)
plt.xticks(rotation=0, horizontalalignment="center")
plt.yticks(rotation=0, horizontalalignment="right")
plt.show()

"""DCEU"""

#Vectorizing
dc_vectorizer = CountVectorizer(      
                             min_df=5, 
                             max_df=0.8,
                             stop_words=stopwords_dc, # remove stop words
                             lowercase=True)       

dc_vectorized = dc_vectorizer.fit_transform(dc_en.clean_text)

# GridSearch for LDA
# Define Search Param

search_params = {'n_components': range(5,15)}

# Init the Model
lda = LatentDirichletAllocation(random_state=42)

# Init Grid Search Class
model_dc = GridSearchCV(lda, param_grid=search_params)

# Do the Grid Search
model_dc.fit(dc_vectorized)

model_dc.cv_results_

#store the result
component_dc={}
for i in range(10):
    component_dc[str(i+5)]= [model_dc.cv_results_['split0_test_score'][i]]
    component_dc[str(i+5)].append(model_dc.cv_results_['split1_test_score'][i])
    component_dc[str(i+5)].append(model_dc.cv_results_['split2_test_score'][i])
    component_dc[str(i+5)].append(model_dc.cv_results_['split3_test_score'][i])
    component_dc[str(i+5)].append(model_dc.cv_results_['split4_test_score'][i])
component_dc=pd.DataFrame(component_dc)

#plot the result
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111)
medianprops = dict(linestyle='-', linewidth=2.5, color='deepskyblue')
plt.boxplot(component_dc, medianprops = medianprops)
ax.set_xticklabels(component_dc.columns)
plt.xticks(rotation=0, horizontalalignment="center")
plt.yticks(rotation=0, horizontalalignment="right")
plt.show()

"""Final topic choice"""

# Display keywork function
def display_topics(model, feature_names, no_top_words):
    for topic_idx, topic in enumerate(model.components_):
        print ("Topic %d:" % (topic_idx))
        print (" ".join([feature_names[i] for i in topic.argsort()[:-no_top_words - 1:-1]]))

# MCU topic with LDA
vectorizer = CountVectorizer(      
                             min_df=5, 
                             max_df=0.8,
                             stop_words=stopwords_mcu,             # remove stop words
                             lowercase=True)  # num chars >       

mcu_vectorized = vectorizer.fit_transform(mcu_en.clean_text)
mcu_feature_names = vectorizer.get_feature_names()
lda_mcu = LatentDirichletAllocation(n_components=8,random_state=42)
lda_mcu.fit(mcu_vectorized)
display_topics(lda_mcu, mcu_feature_names, no_top_words=15)

# MCU topic with NMF
vectorizer = CountVectorizer(      
                             min_df=5, 
                             max_df=0.8,
                             stop_words=stopwords_mcu,             # remove stop words
                             lowercase=True)  # num chars >       

mcu_vectorized = vectorizer.fit_transform(mcu_en.clean_text)
mcu_feature_names = vectorizer.get_feature_names()
nmf_mcu = NMF(n_components=8,random_state=42)
nmf_mcu.fit(mcu_vectorized)
display_topics(nmf_mcu, mcu_feature_names, no_top_words=15)

# DC topic with LDA
vectorizer = CountVectorizer(      
                             min_df=5, 
                             max_df=0.8,
                             stop_words=stopwords_dc, # remove stop words
                             lowercase=True)        

dc_vectorized = vectorizer.fit_transform(dc_en.clean_text)
dc_feature_names = vectorizer.get_feature_names()
lda_dc = LatentDirichletAllocation(n_components=6,random_state=42)
lda_dc.fit(dc_vectorized)
display_topics(lda_dc, dc_feature_names, no_top_words=15)

# MCU topic with NMF
vectorizer = CountVectorizer(      
                             min_df=5, 
                             max_df=0.8,
                             stop_words=stopwords_dc,             # remove stop words
                             lowercase=True)  # num chars >       

dc_vectorized = vectorizer.fit_transform(dc_en.clean_text)
dc_feature_names = vectorizer.get_feature_names()
nmf_dc = NMF(n_components=6,random_state=42)
nmf_dc.fit(dc_vectorized)
display_topics(nmf_dc, dc_feature_names, no_top_words=15)

"""Index of each topic"""

#MCU - Embded tweet with topic
mcu_topic=nmf_mcu.transform(mcu_vectorized)
mcu_en['topic']=mcu_topic.argmax(axis=1)
mcu_en.head()

#MCU - Volumn, sentiment and verbatim of topic
for i in range(8):
    print ('Topic {} has {} tweets, accounting for {}% of total volume. The positive percentage is {}%, negative is {}% and neutral is {}%'.format (
        i, len(mcu_en[mcu_en.topic==i]), len(mcu_en[mcu_en.topic==i])*100/len(mcu_en), 
        len(mcu_en[(mcu_en.topic==i) & (mcu_en.sentiment=='positive')])*100/len(mcu_en[mcu_en.topic==i]),
        len(mcu_en[(mcu_en.topic==i) & (mcu_en.sentiment=='negative')])*100/len(mcu_en[mcu_en.topic==i]),
        len(mcu_en[(mcu_en.topic==i) & (mcu_en.sentiment=='neutral')])*100/len(mcu_en[mcu_en.topic==i])))
    print (mcu_en[(mcu_en.topic==i)]['full_text'].head(20))

#Negative tweets on Topic 7
for i in mcu_en[(mcu_en.topic==7)&(mcu_en.sentiment=='negative')]['full_text']:
    print(i)

#DC - Embded tweet with topic
dc_topic=nmf_dc.transform(dc_vectorized)
dc_en['topic']=dc_topic.argmax(axis=1)
dc_en.head()

#DC - Volumn, sentiment and verbatim of topic
for i in range(6):
    print ('Topic {} has {} tweets, accounting for {}% of total volume. The positive percentage is {}%, negative is {}% and neutral is {}%'.format (
        i, len(dc_en[dc_en.topic==i]), len(dc_en[dc_en.topic==i])*100/len(dc_en), 
        len(dc_en[(dc_en.topic==i) & (dc_en.sentiment=='positive')])*100/len(dc_en[dc_en.topic==i]),
        len(dc_en[(dc_en.topic==i) & (dc_en.sentiment=='negative')])*100/len(dc_en[dc_en.topic==i]),
        len(dc_en[(dc_en.topic==i) & (dc_en.sentiment=='neutral')])*100/len(dc_en[dc_en.topic==i])))
    print (dc_en[(dc_en.topic==i)]['full_text'].head(20))

#Negative in topic 0 (mostly retweet article)
for i in dc_en[(dc_en.topic==0)&(dc_en.sentiment=='negative')]['full_text']:
    print(i)

#Negative in topic 4 (mostly reply)
for i in dc_en[(dc_en.topic==4)&(dc_en.sentiment=='negative')]['full_text']:
    print(i)

#Negative in topic 2
for i in dc_en[(dc_en.topic==2)&(dc_en.sentiment=='negative')]['full_text']:
    print(i)

for i in dc_en[dc_en.topic==5]['full_text']:
    print(i)

"""Entity detection"""

#MCU
#Function to ngram
from sklearn.feature_extraction.text import CountVectorizer
def get_top_n_gram(corpus,ngram_range,n=None):
    vec = CountVectorizer(ngram_range=ngram_range,stop_words = stopwords_mcu).fit(corpus)
    bag_of_words = vec.transform(corpus)
    sum_words = bag_of_words.sum(axis=0) 
    words_freq = [(word, sum_words[0, idx]) for word, idx in vec.vocabulary_.items()]
    words_freq =sorted(words_freq, key = lambda x: x[1], reverse=True)
    return words_freq[:n]
#n2_bigram
n2_bigrams = get_top_n_gram(mcu_en.clean_text,(2,2),20)
n2_bigrams

#DC
#Function to ngram
from sklearn.feature_extraction.text import CountVectorizer
def get_top_n_gram(corpus,ngram_range,n=None):
    vec = CountVectorizer(ngram_range=ngram_range,stop_words = stopwords_dc).fit(corpus)
    bag_of_words = vec.transform(corpus)
    sum_words = bag_of_words.sum(axis=0) 
    words_freq = [(word, sum_words[0, idx]) for word, idx in vec.vocabulary_.items()]
    words_freq =sorted(words_freq, key = lambda x: x[1], reverse=True)
    return words_freq[:n]
#n2_bigram
n2_bigrams = get_top_n_gram(dc_en.clean_text,(2,2),20)
n2_bigrams

#save sentiment processing
mcu_en.to_csv('mcu_sentiment.csv',index=None)
dc_en.to_csv('dc_sentiment.csv',index=None)

"""## Network analysis"""

mcu_sentiment=pd.read_csv('mcu_sentiment.csv')
dc_sentiment=pd.read_csv('dc_sentiment.csv')

"""MCU"""

#sliced the network data
mcu_network=mcu_sentiment[mcu_sentiment.network.isnull()==False][['user_id','network']]

#remove self-reply
mcu_network=mcu_network[mcu_network.user_id!=mcu_network.network]

#save to csv
mcu_network.to_csv('mcu_network.csv',header=None, index=None)

#loading the data
G = nx.read_edgelist("mcu_network.csv", delimiter=',', create_using=nx.DiGraph())

# nodes & edges
print(len(G.nodes))
print(len(G.edges))

#%density
nx.density(G)*100

#store the top list of closeness, betweenness, degree, in-degree
sorted_closeness = sorted(nx.closeness_centrality(G).items(), key=lambda kv: kv[1], reverse=True)
sorted_betweenness = sorted(nx.betweenness_centrality(G).items(), key=lambda kv: kv[1], reverse=True)
sorted_indegree = sorted(dict(G.in_degree()).items(), key=lambda kv: kv[1], reverse=True)
sorted_degree = sorted(dict(G.degree()).items(), key=lambda kv: kv[1], reverse=True)

#check account profile based on top in-degree
for i in sorted_indegree[:30]:
    try:
        # obtain their twitter user information
        profile = twitter_api.users.lookup(user_id=int(float(i[0])))
        # calculating the sentiment of their retweet (meaning their original post) & replies towards them
        sentiment = mcu_sentiment.loc[mcu_sentiment.network==int(float(i[0])),'sentiment']
        print ('- {} ({} - ID: {}) has {} followers, {} interacts from MCU fanbase and {} interacts from DC fanbase'.format(profile[0]['name'], profile[0]['screen_name'] , profile[0]['id'] , profile[0]['followers_count'], i[1], len(dc_network[dc_network.network==float(i[0])])))
        print(sentiment.value_counts()/(len(sentiment)))
    except:
        # inform of deactivated account
        print ('-', int(float(i[0])), 'Error account - deactivated')

"""DCEU"""

#sliced the network data
#remove self-reply
dc_network=dc_sentiment[dc_sentiment.network.isnull()==False][['user_id','network']]
dc_network=dc_network[dc_network.user_id!=dc_network.network]

#save the data
dc_network.to_csv('dc_network.csv',header=None, index=None)

#load the data
dc_network=pd.read_csv('dc_network.csv')
dc_network.columns = ['user_id','network']

#load the data
G1 = nx.read_edgelist("dc_network.csv", delimiter=',', create_using=nx.DiGraph())

#edges, nodes
print(len(G1.nodes))
print(len(G1.edges))

#%density
nx.density(G1)*100

#calculate closeness, betweenness, degree
sorted_closeness1 = sorted(nx.closeness_centrality(G1).items(), key=lambda kv: kv[1], reverse=True)
sorted_betweenness1 = sorted(nx.betweenness_centrality(G1).items(), key=lambda kv: kv[1], reverse=True)
sorted_indegree1 = sorted(dict(G1.in_degree()).items(), key=lambda kv: kv[1], reverse=True)
sorted_degree1 = sorted(dict(G1.degree()).items(), key=lambda kv: kv[1], reverse=True)

#check account profile based on top in-degree
for i in sorted_indegree1[:30]:
    try:
        # obtain their twitter user information
        profile = twitter_api.users.lookup(user_id=int(float(i[0])))
        # calculate sentiment of their retweet & reply
        sentiment = dc_sentiment.loc[dc_sentiment.network==int(float(i[0])),'sentiment']
        print ('- {} ({} - ID: {}) has {} followers, {} interacts from DC fanbase and {} interacts from MCU fanbase'.format(profile[0]['name'], profile[0]['screen_name'] , profile[0]['id'] , profile[0]['followers_count'], i[1], len(mcu_network[mcu_network.network==float(i[0])])))
        print(sentiment.value_counts()/(len(sentiment)))
    except:
        # inform of activated account 
        print ('-', int(float(i[0])), 'Error account - deactivated')

#Total interact between two fandom
# mcu user in dc base
mutual_user=0
for i in mcu_sentiment.user_id.unique():
    for j in dc_sentiment.user_id.unique():
        if i == j :
            mutual_user+=1

# mcu user reply/ retweet dc base
mcu_interact_with_dc=0
for i in mcu_network.network.unique():
    for j in dc_sentiment.user_id.unique():
        if i == j:
            mcu_interact_with_dc+=1
            
# dc user reply/ retweet mcu base
dc_interact_with_mcu=0
for i in dc_network.network.unique():
    for j in mcu_sentiment.user_id.unique():
        if i == j:
            dc_interact_with_mcu+=1
        
print(mutual_user)
print(mcu_interact_with_dc)
print(dc_interact_with_mcu)

# % among mcu target node
1108/mcu_network.network.nunique()

/mcu_network.network.nunique()

mcu_clean.user[0]

