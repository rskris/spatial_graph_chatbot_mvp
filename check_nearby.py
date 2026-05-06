import pandas as pd
import geopandas as gpd
from shapely import wkt
from chatbot import PropertyGraphChatbot

bot = PropertyGraphChatbot()
node = bot.find_node("600 North Rosemead Boulevard")
geom = bot.nodes_gdf[bot.nodes_gdf['node_id'] == node['node_id']].iloc[0].geometry
buffer = geom.buffer(1000) # Check within 1km
nearby = bot.places[bot.places.geometry.within(buffer)]
print("Places within 1km:")
print(nearby[['name', 'category']].head(20))
