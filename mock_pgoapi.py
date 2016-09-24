#!/usr/bin/env python
import random
import json
import time
from math import radians, cos, sin, asin, sqrt

import s2sphere
from s2sphere import CellId, math, Cap, LatLng, Angle
from s2sphere import LatLng, Angle, Cap, RegionCoverer, math

from mock_api_response_template import *


EARTH_RADIUS = 6371000  # radius of Earth in meters

class AuthProvider():
    def __init__(self):
        self._access_token = "123"
        self._refresh_token = "123"

    def set_ticket(self, ticket):
        return

    def get_ticket(self):
        return



class Pokemon(object):
    def __init__(self, pokemon_id, longitude, latitude, expire, spawn_point_id, encounter_id):
        self.pokemon_id = pokemon_id
        self.longitude = longitude
        self.latitude = latitude
        self.expire = expire
        self.spawn_point_id = spawn_point_id
        self.encounter_id = encounter_id

    def __str__(self):
        return "|id: {0}, expire: {1}, longitude: {2}, latitude: {3}|".format(self.pokemon_id, 
                                                                            self.longitude, 
                                                                            self.latitude, 
                                                                            self.expire)

    def __repr__(self):
        return str(self)

    def haversine(self, lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        meters = EARTH_RADIUS * c
        return meters

    def is_catchable_pokemon(self, user_latitude, user_longitude):
        distance = self.haversine(self.longitude,
                                  self.latitude,
                                  user_longitude,
                                  user_latitude) 
        if distance < 200:
            return True
        return False

    def get_catchable_pokemon_representation(self):
        result = {
              "pokemon_id": self.pokemon_id, 
              "longitude": self.longitude, 
              "expiration_timestamp_ms": self.expire * 1000, 
              "latitude": self.latitude, 
              "spawn_point_id": str(self.spawn_point_id), 
              "encounter_id": self.encounter_id
            }
        return result 

    def get_wild_pokemon_representation(self):
        result = {
              "last_modified_timestamp_ms": self.expire * 1000, 
              "longitude": self.longitude, 
              "pokemon_data": {
                "pokemon_id": self.pokemon_id
              }, 
              "latitude": self.latitude, 
              "spawn_point_id": self.spawn_point_id, 
              "encounter_id": self.encounter_id, 
              "time_till_hidden_ms": (self.expire - time.time()) * 1000  
            }
        return result


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

        self._auth_provider = AuthProvider() 

        self.set_api_endpoint("pgorelease.nianticlabs.com/plfe")

        self._signature_lib = None

        self._session = None

        self.device_info = None 

    def set_position(self, latitude, longitude, height):
        self.longitude = longitude
        self.latitude = latitude
        self.height = height


    def get_api_endpoint(self):
        return ""

    def activate_signature(self, shared_library):
        return

    def set_authentication(self, provider, username, password, proxy_config=None):
        return

    def set_proxy(self, proxy):
        return

    def set_api_endpoint(self, endpoint):
        return

    def get_sub_cells(self, cellid, level=1):
        sub_cells = []
        start = CellId(id_=cellid).child_begin()
        end = CellId(id_=cellid).child_end()
        while ( start.id() < end.id() ):
            if level == 1:
                sub_cells.append(start.id())
            else:
                sub_cells += self.get_sub_cells(start.id(), level-1)
            start = start.next()
        return sub_cells



    def generate_pokemon_by_cellid_timestamp(self, cellid, timestamp, max_pokemon):
        """ Return a list of pokemon in that cellid """
        # Use cellid|timestamp as random seed
        random.seed(str(cellid) + str(timestamp / 60))

        # Get all sub cellids
        sub_cells = self.get_sub_cells(cellid, 2)

        # Random sample from sub cellids
        poke_count = random.randrange(0, max_pokemon + 1)
        poke_cells = random.sample(sub_cells, poke_count)

        # Generate random pokemon ids
        result = []
        for poke_cell in poke_cells:
            pokemon_id = random.randrange(1, 494)
            latitude, longitude, height = get_position_from_cellid(poke_cell)
            expire = timestamp + random.randrange(300, 900)
            next_pokemon = Pokemon(pokemon_id, longitude, latitude, expire, poke_cell, poke_cell + expire)
            result.append(next_pokemon)
        return result

    def get_nearby_pokemons(self, latitude, longitude, timestamp):
        """ Return a map { "cellid" : [ list of pokemons ] } """
        # Get surrounding cell ids from latitude and longitude
        surrounding_cells = get_surrounding_cell_ids(latitude, longitude, 200)
        
        # Generate pokemons for each surrounding cells
        result = {}
        for cell in surrounding_cells:
            if cell not in result:
                result[cell] = []
            for sub_timestamp in range(int(timestamp - 300), int(timestamp + 300), 60):
                result[cell] += self.generate_pokemon_by_cellid_timestamp(cell, sub_timestamp, 1)


             
        return result

    def get_map_objects(self, latitude, longitude, since_timestamp_ms, cell_id):
        # Get all pokemons
        cell_pokemons_map = self.get_nearby_pokemons(latitude, longitude, time.time())

        map_cells = []
        # Assign pokemon to each cell in cell_id by distance
        for cell_id_str in cell_id:
            cell_id_long = long(cell_id_str)

            # Add standard field
            map_cell = {
                "s2_cell_id": cell_id_long, 
                "current_timestamp_ms": time.time() * 1000, 
            }

            # Check if current cell have pokemon
            cell_id_level15 = (cell_id_long / 536870912) * 536870912 
            if cell_id_level15 in cell_pokemons_map:
                for pokemon in cell_pokemons_map[cell_id_level15]:
                    # For each pokemon, check its distance to user
                    if pokemon.is_catchable_pokemon(latitude, longitude):
                        if "catchable_pokemons" not in map_cell:
                            map_cell["catchable_pokemons"] = []
                        map_cell["catchable_pokemons"].append(pokemon.get_catchable_pokemon_representation())
                    # For pokemon near, assign to catchable pokemon
                    else:
                        if "wild_pokemons" not in map_cell:
                            map_cell["wild_pokemons"] = []
                        map_cell["wild_pokemons"].append(pokemon.get_wild_pokemon_representation())

            map_cells.append(map_cell)

        # Add fort information

        response = GET_MAP_OBJECT_RESPONSE_TEMPLATE 
        response["responses"]["GET_MAP_OBJECTS"]["map_cells"] = map_cells

        # Sleep random second to simulate network delay
        time.sleep(random.randrange(0,8))

        return response

if __name__ == "__main__":
    api = PGoApi()
    cells = [9937791469106495488L, 9937791471253979136L, 9937791492728815616L, 9937791481991397376L, 9937791572185710592L, 9937791578628161536L, 9937791509908684800L, 9937791580775645184L, 9937791494876299264L, 9937791486286364672L, 9937791501318750208L, 9937791473401462784L, 9937791497023782912L, 9937791490581331968L, 9937791499171266560L, 9937791503466233856L, 9937791512056168448L, 9937791477696430080L, 9937791475548946432L, 9937791479843913728L, 9937791484138881024L, 9937791488433848320L]
    api.set_position(40, -73, 0)
    print json.dumps(api.get_map_objects(40, -73, [0] * len(cells), cells), indent=2)

