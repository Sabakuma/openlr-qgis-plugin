from __future__ import annotations
from openlr_dereferencer.maps import MapReader
from openlr_dereferencer.maps import Line as AbstractLine, Node as AbstractNode
import psycopg2 as pg
from psycopg2 import sql
from openlr import Coordinates, FOW, FRC
from shapely import wkb
from itertools import chain
from shapely.geometry import LineString, Point
from typing import Iterable, Hashable, Sequence, cast
from pyproj import Geod
from shapely.ops import nearest_points

GEOD = Geod(ellps="WGS84")

class MyLine(AbstractLine):
    
    def __init__(self, map_reader: MyMapReader, line_id: int, fow: FOW, frc: FRC, length: float, from_int: int | MyNode, to_int: int | MyNode, geometry: LineString):
        self.id = line_id
        self.map_reader = map_reader
        self._fow: FOW = fow
        self._frc: FRC = frc
        self._length: float = length
        self.from_int: int | MyNode = from_int
        self.to_int: int | MyNode = to_int
        self._geometry: LineString = geometry

    @property
    def line_id(self) -> Hashable:
        return self.id

    @property
    def start_node(self) -> MyNode:
        if isinstance(self.from_int, MyNode):
            return self.from_int
        else:
            self.from_int = self.map_reader.get_node(self.from_int)
            return self.from_int

    @property
    def end_node(self) -> MyNode:
        if isinstance(self.to_int, MyNode):
            return cast(MyNode, self.to_int)
        else:
            self.to_int = self.map_reader.get_node(cast(int, self.to_int))
            return self.to_int

    @property
    def frc(self) -> FRC:
        return self._frc

    @property
    def length(self) -> float:
        return self._length
    
    @property
    def fow(self) -> FOW:
        return self._fow

    @property
    def geometry(self) -> LineString:
        return self._geometry

    def coordinates(self) -> Sequence[Coordinates]:
        return [Coordinates(*point) for point in self.geometry.coords]

    def distance_to(self, coord: Coordinates) -> int:
        return GEOD.geometry_length(LineString(nearest_points(self._geometry, Point(coord.lon, coord.lat))))

class MyNode(AbstractNode):

    def __init__(self, map_reader: MyMapReader, node_id: int, lon: float, lat: float):
        self.lon = lon
        self.lat = lat
        self.map_reader = map_reader
        self.id = node_id

    @property
    def node_id(self) -> Hashable:
        return self.id

    @property
    def coordinates(self) -> Coordinates:
        return Coordinates(lon=self.lon, lat=self.lat)

    def outgoing_lines(self) -> Iterable[MyLine]:
        with self.map_reader.connection.cursor() as cursor:
            cursor.execute(self.map_reader.outgoing_lines_query, (self.node_id, self.node_id))
            for (line_id, fow, flowdir, frc, length, from_int, to_int, geom) in cursor:
                ls = LineString(wkb.loads(geom, hex=True))
                yield MyLine(self.map_reader, line_id, FOW(fow), FRC(frc), length, self, to_int, ls)
        
    def incoming_lines(self) -> Iterable[MyLine]:
        with self.map_reader.connection.cursor() as cursor:
            cursor.execute(self.map_reader.incoming_lines_query, (self.node_id, self.node_id))
            for (line_id, fow, flowdir, frc, length, from_int, to_int, geom) in cursor:
                ls = LineString(wkb.loads(geom, hex=True))
                yield MyLine(self.map_reader, line_id, FOW(fow), FRC(frc), length, from_int, self, ls)

    def connected_lines(self) -> Iterable[MyLine]:
        return chain(self.incoming_lines(), self.outgoing_lines())

@MapReader.register
class MyMapReader:

    SCHEMA = 'public'
    TABLE_LINE = 'roads'
    TABLE_NODE = 'intersections'
    
    NODE_QUERY_SELECT = "select id,st_x(geom),st_y(geom)"
    NODE_QUERY = NODE_QUERY_SELECT + " from {schema}.{table}"
    LINE_QUERY_SELECT = "select id,fow,flowdir,frc,len,from_int,to_int,geom"
    REV_LINE_QUERY_SELECT = "select -id,fow,flowdir,frc,len,to_int as from_int,from_int as to_int,st_reverse(geom)"
    LINE_QUERY = LINE_QUERY_SELECT + " from {schema}.{table}"
    REV_LINE_QUERY = REV_LINE_QUERY_SELECT + " from {schema}.{table}"

    def __init__(self, user: str, password: str, dbname: str, **kwargs):
        super().__init__(**kwargs)

        self.connection = pg.connect(host='127.0.0.1', port='5432', user=user, password=password, dbname=dbname)
        self.get_linecount_query = sql.SQL("select count(1) from {schema}.{table}").format(schema=sql.Identifier(self.SCHEMA), table=sql.Identifier(self.TABLE_LINE))
        self.get_node_query = sql.SQL(self.NODE_QUERY + " where id=%s").format(schema=sql.Identifier(self.SCHEMA), table=sql.Identifier(self.TABLE_NODE))
        self.get_nodes_query = sql.SQL(self.NODE_QUERY).format(schema=sql.Identifier(self.SCHEMA), table=sql.Identifier(self.TABLE_NODE))
        self.get_nodecount_query = sql.SQL("select count(1) from {schema}.{table}").format(schema=sql.Identifier(self.SCHEMA), table=sql.Identifier(self.TABLE_NODE))
        self.get_lines_query = sql.SQL(self.LINE_QUERY + " where flowdir in (1,3) union " + self.REV_LINE_QUERY + " where flowdir in (1,2)").format(schema=sql.Identifier(self.SCHEMA), table=sql.Identifier(self.TABLE_LINE))        
        self.find_nodes_close_to_query = sql.SQL(self.NODE_QUERY + " where geom && st_buffer(ST_GeographyFromText('SRID=4326;POINT(%s %s)'), %s)::geometry").format(schema=sql.Identifier(self.SCHEMA), table=sql.Identifier(self.TABLE_NODE))
        self.find_lines_close_to_query = sql.SQL(f"""
                                                    with sq as ({self.LINE_QUERY} where geom && st_buffer(ST_GeographyFromText('SRID=4326;POINT(%s %s)'), %s)::geometry)
                                                        ({self.LINE_QUERY_SELECT} from sq where sq.flowdir in (1,3)) 
                                                        union 
                                                        ({self.REV_LINE_QUERY_SELECT} from sq where sq.flowdir in (1,2))
                                                """).format(schema=sql.Identifier(self.SCHEMA),
                                                            table=sql.Identifier(self.TABLE_LINE))
        self.incoming_lines_query = sql.SQL(self.LINE_QUERY + " where to_int = %s and flowdir in (1,3) union " + self.REV_LINE_QUERY + " where from_int = %s and flowdir in (1,2)").format(table=sql.Identifier(self.TABLE_LINE), schema=sql.Identifier(self.SCHEMA))
        self.outgoing_lines_query = sql.SQL(self.LINE_QUERY + " where from_int = %s and flowdir in (1,3) union " + self.REV_LINE_QUERY + " where to_int = %s and flowdir in (1,2)").format(table=sql.Identifier(self.TABLE_LINE), schema=sql.Identifier(self.SCHEMA))

    def get_line(self, line_id: Hashable) -> MyLine:
        with self.connection.cursor() as cursor:
            cursor.execute(self.get_lines_query)
            for (line_id, fow, flowdir, frc, length, from_int, to_int, geom) in cursor:
                if line_id == line_id:
                    ls = LineString(wkb.loads(geom, hex=True))
                    return MyLine(self, line_id, FOW(fow), FRC(frc), length, from_int, to_int, ls)
        raise Exception(f"Line with ID {line_id} not found")

    def get_lines(self) -> Iterable[MyLine]:
        with self.connection.cursor() as cursor:
            cursor.execute(self.get_lines_query)
            for (line_id, fow, flowdir, frc, length, from_int, to_int, geom) in cursor:
                ls = LineString(wkb.loads(geom, hex=True))
                yield MyLine(self, line_id, FOW(fow), FRC(frc), length, from_int, to_int, ls)

    def get_linecount(self) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(self.get_linecount_query)
            res = cursor.fetchone()
            if res is None:
                raise Exception("Error retrieving line count from datastore")
            (count,) = res
            return count

    def get_node(self, node_id: Hashable) -> MyNode:
        with self.connection.cursor() as cursor:
            cursor.execute(self.get_node_query, (node_id,))
            res = cursor.fetchone()
            if res is None:
                raise Exception(f"Error retrieving node {node_id} from datastore")
            (node_id, lon, lat) = res
            return MyNode(self, node_id, lon, lat)

    def get_nodes(self) -> Iterable[MyNode]:
        with self.connection.cursor() as cursor:
            cursor.execute(self.get_nodes_query)
            for (node_id, lon, lat) in cursor:
                yield MyNode(self, node_id, lon, lat)

    def get_nodecount(self) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(self.get_nodecount_query)
            res = cursor.fetchone()
            if res is None:
                raise Exception(f"Error retrieving node count from datastore")
            (count,) = res
            return count

    def find_nodes_close_to(self, coord: Coordinates, dist: float) -> Iterable[MyNode]:
        lon, lat = coord.lon, coord.lat
        with self.connection.cursor() as cursor:
            cursor.execute(self.find_nodes_close_to_query, (lon, lat, dist))
            for (node_id, lon, lat) in cursor:
                yield MyNode(self, node_id, lon, lat)

    def find_lines_close_to(self, coord: Coordinates, dist: float) -> Iterable[MyLine]:
        lon, lat = coord.lon, coord.lat
        with self.connection.cursor() as cursor:
            cursor.execute(self.find_lines_close_to_query, (lon, lat, dist))
            for (line_id, fow, _, frc, length, from_int, to_int, geom) in cursor:
                ls = LineString(wkb.loads(geom, hex=True))
                yield MyLine(self, line_id, FOW(fow), FRC(frc), length, from_int, to_int, ls)
