# Import the geopandas library</span>
import geopandas as gpd

# Read the shapefile</span>
gdf = gpd.read_file("shapefile.shp")

# Assign a new column that is the difference of column "Applied" and "Target"
gdf["Difference"] = gdf["Applied"] - gdf["Target"]

# Apply 2*x to column "distance"</span>
gdf["distance"] = gdf["distance"] * 2
# Save the modified shapefile
gdf.to_file("modified_shapefile.shp")