def cloudcover_func(cloudcover_max, start_year,footprint_path):
    from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
    from shapely.ops import transform

    from datetime import date
    import pandas as pd
    import geopandas as gpd


    api = SentinelAPI('Naderschah', '', 'https://apihub.copernicus.eu/apihub')

    # Here we can create our footprint, to creae a file go here: https://geojsoncreator.com/
    footprint = geojson_to_wkt(read_geojson(footprint_path))
    start_date = date(start_year, 1, 1)

    # Now we can query (MSI 2A data product)
    products = api.query(footprint,
                        date = (start_date, date(start_date.year, 12, 31)),
                        platformname = 'Sentinel-2',
                        cloudcoverpercentage = (0, cloudcover_max))

    # Get meta data, as this contains geograpy and cloud percentages its all we actually need
    meta = api.to_geodataframe(products)
    # Only select level 2A products
    meta = meta[meta.title.apply(lambda x:x.startswith('S2B_MSIL2A'))]



    import datetime as dt 
    # Format date column
    meta['Date'] = meta.summary.apply(lambda x: dt.datetime.strptime(x.split(",")[0].strip("Date: ").split('.')[0].strip(' '), "%Y-%m-%dT%H:%M:%S"))
    # TODO: Filter somehow accoridng to sundown and sunup and then see what can be done 
    #meta = meta.Date[meta.Data]
    def flip(x, y):
        """Flips the x and y coordinate values"""
        return y, x

    # Get outer perimeter:
    import shapely
    perim = transform(flip,shapely.wkt.loads(footprint))


    minx, miny, maxx, maxy = perim.bounds
    scaler = 50
    minx= int((minx)//1)  
    miny= int((miny)//1)  
    maxx= int((maxx)//1+1)
    maxy= int((maxy)//1+1)


    import numpy as np
    date_array = np.empty(shape=((maxx-minx)*scaler, scaler*(maxy-miny)),dtype='datetime64[ns]')
    date_array[:] = np.datetime64("NaT")


    # Really inefficient need to find a better way of doing this
    for x in range(len(date_array)):
        for y in range(len(date_array[x])):
            # reestablish coordinate
            lat = y/scaler + miny
            lon = x/scaler + minx
            # Check if they intersect with any polygon in the geopandas array
            bool_series = meta.geometry.contains(shapely.Point(lat,lon))
            # Grab dates
            # TODO: the below evaluates to nan for all where cloudcoverpercentage is not nan need to find out details before moving on
            if len(meta[bool_series].Date.dropna())>0 : 
                date_array[x,y] = meta[bool_series].Date.dropna().min().to_numpy().astype('datetime64[ns]')
            

    date_range = date_array.flatten()
    date_range = date_range[~np.isnan(date_range)]
    print("Starting obs on the: {}".format(start_date))
    print("Cloudcover max: {}".format(cloudcover_max))
    print("Surface area subdivisions: {}".format(scaler))
    print("Earliest Possible: {}".format(np.datetime_as_string(date_range.min(), unit='D')))
    print("Earliest time of full observation of footprint: {}".format(np.datetime_as_string(date_range.max(), unit='D')))