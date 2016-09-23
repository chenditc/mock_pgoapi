#!/usr/bin/env python
import random
import json

import s2sphere
from s2sphere import CellId, math, Cap, LatLng, Angle
from s2sphere import LatLng, Angle, Cap, RegionCoverer, math


EARTH_RADIUS = 6371000  # radius of Earth in meters

def get_position_from_cellid(cellid):
    cell = CellId(id_ = cellid).to_lat_lng()
    return (math.degrees(cell._LatLng__coords[0]), math.degrees(cell._LatLng__coords[1]), 0)

def get_surrounding_cell_ids(lat, long, radius=1000):
    # Max values allowed by server according to this comment:
    # https://github.com/AeonLucid/POGOProtos/issues/83#issuecomment-235612285
    if radius > 1500:
        radius = 1500  # radius = 1500 is max allowed by the server
    region = Cap.from_axis_angle(LatLng.from_degrees(lat, long).to_point(), Angle.from_degrees(360*radius/(2*math.pi*EARTH_RADIUS)))
    coverer = RegionCoverer()
    coverer.min_level = 15
    coverer.max_level = 15
    cells = coverer.get_covering(region)
    return sorted([x.id() for x in cells])



class PGoApi(object):
    def __init__(self):
        self.latitude = 0
        self.longitude = 0
        self.height = 0

    def set_position(self, latitude, longitude, height):
        self.position = longitude
        self.latitude = latitude
        self.height = height

    def generate_pokemon_by_cellid_timestamp(self, cellid, timestamp):
        """ Return a list of pokemon in that cellid """
        # Use cellid|timestamp as random seed
        random.seed(str(cellid) + str(timestamp))

        # Get all sub cellids
        start = CellId(id_=cellid).child_begin()
        end = CellId(id_=cellid).child_end()
        sub_cells = []
        while ( start.id() < end.id() ):
            sub_cells.append(start.id())
            start = start.next()
       
        # Random sample from sub cellids
        poke_count = random.randrange(0,len(sub_cells))
        poke_cells = random.sample(sub_cells, poke_count)

        # Generate random pokemon ids
        result = []
        for poke_cell in poke_cells:
            pokemon_id = random.randrange(1, 494)
            latitude, longitude, height = get_position_from_cellid(poke_cell)
            result.append({ "pokemon_id" : pokemon_id,
                            "latitude" : latitude,
                            "longitude" : longitude })
        return result

    def get_nearby_pokemons(self, latitude, longitude, timestamp):
        """ Return a map { "cellid" : [ list of pokemons ] } """
        # Get surrounding cell ids from latitude and longitude
        surrounding_cells = get_surrounding_cell_ids(latitude, latitude, 500)
        
        # Generate pokemons for each surrounding cells
        result = {}
        for cell in surrounding_cells:
            if cell not in result:
                result[cell] = []
            result[cell].append(self.generate_pokemon_by_cellid_timestamp(cell, timestamp))
             
        return result

    def get_map_objects(self, latitude, longitude, since_timestamp_ms, cell_id):
        # Get all pokemons

        # Assign pokemon to each cell in cell_id by distance

        # Add fort information

        return {}

api = PGoApi()
print json.dumps(api.get_map_objects(40, -73, [0], [0]), indent=2)

print api.get_nearby_pokemons(40, -73, 1474603639) 
