"""Fetch a small EDDF OSM extract and keep airport geometry only (stdlib)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
# Four bounded requests stay below the OSM API's per-request node limit.
BBOXES = [
    '8.50,50.01,8.555,50.035', '8.555,50.01,8.61,50.035',
    '8.50,50.035,8.555,50.06', '8.555,50.035,8.61,50.06',
]
nodes = {}
ways = {}
airport_relations = {}
for bbox in BBOXES:
    url = 'https://www.openstreetmap.org/api/0.6/map?bbox=' + bbox.replace(',', '%2C')
    request = Request(url, headers={'User-Agent': 'aiw26-airport-layer/0.1 (https://github.com/abecic-pr/aiw26)'})
    with urlopen(request, timeout=45) as response:
        document = ET.fromstring(response.read())
    for node in document.findall('node'):
        nodes[node.attrib['id']] = [float(node.attrib['lon']), float(node.attrib['lat'])]
    for way in document.findall('way'):
        tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}
        if tags.get('aeroway') in ('aerodrome', 'runway', 'terminal'):
            ways[way.attrib['id']] = (way, tags)
    for relation in document.findall('relation'):
        tags = {tag.attrib['k']: tag.attrib['v'] for tag in relation.findall('tag')}
        if tags.get('aeroway') == 'aerodrome' and tags.get('icao') == 'EDDF':
            airport_relations[relation.attrib['id']] = relation
    print('Fetched', bbox, flush=True)

features = []
for relation_id in airport_relations:
    url = 'https://www.openstreetmap.org/api/0.6/relation/' + relation_id + '/full'
    with urlopen(Request(url, headers={'User-Agent': 'aiw26-airport-layer/0.1 (https://github.com/abecic-pr/aiw26)'}), timeout=45) as response:
        document = ET.fromstring(response.read())
    for node in document.findall('node'):
        nodes[node.attrib['id']] = [float(node.attrib['lon']), float(node.attrib['lat'])]
    full_ways = {way.attrib['id']: [nd.attrib['ref'] for nd in way.findall('nd')] for way in document.findall('way')}
    relation = next(item for item in document.findall('relation') if item.attrib['id'] == relation_id)
    segments = [full_ways[member.attrib['ref']] for member in relation.findall('member') if member.attrib['type'] == 'way' and member.attrib.get('role') == 'outer']
    rings = []
    while segments:
        ring = segments.pop(0)[:]
        while ring[0] != ring[-1]:
            for index, segment in enumerate(segments):
                if segment[0] == ring[-1]:
                    ring.extend(segment[1:]); segments.pop(index); break
                if segment[-1] == ring[-1]:
                    ring.extend(list(reversed(segment))[1:]); segments.pop(index); break
            else:
                raise RuntimeError('Airport boundary has an incomplete ring')
        rings.append([[nodes[ref] for ref in ring]])
    tags = {tag.attrib['k']: tag.attrib['v'] for tag in relation.findall('tag')}
    features.append({'type': 'Feature', 'id': 'relation/' + relation_id,
        'properties': {**tags, 'osmUrl': 'https://www.openstreetmap.org/relation/' + relation_id},
        'geometry': {'type': 'MultiPolygon', 'coordinates': rings}})
for osm_id, (way, tags) in ways.items():
    coordinates = [nodes[node.attrib['ref']] for node in way.findall('nd')]
    if len(coordinates) < 2:
        continue
    polygon = coordinates[0] == coordinates[-1] and tags['aeroway'] != 'runway'
    features.append({
        'type': 'Feature', 'id': 'way/' + osm_id,
        'properties': {**tags, 'osmUrl': 'https://www.openstreetmap.org/way/' + osm_id},
        'geometry': {'type': 'Polygon' if polygon else 'LineString', 'coordinates': [coordinates] if polygon else coordinates},
    })
runways = {feature['properties'].get('ref') for feature in features if feature['properties']['aeroway'] == 'runway'}
expected = {'07L/25R', '07C/25C', '07R/25L', '18'}
if not expected.issubset(runways):
    raise RuntimeError('Missing expected runway references: ' + str(expected - runways))
if not any(feature['properties']['aeroway'] == 'aerodrome' for feature in features):
    raise RuntimeError('Airport boundary missing; previous extract has not been replaced')
output = ROOT / 'public/data/frankfurt-airport.geojson'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({
    'type': 'FeatureCollection',
    'source': 'https://www.openstreetmap.org',
    'license': 'ODbL-1.0',
    'attribution': '© OpenStreetMap contributors',
    'retrievedAt': datetime.now(timezone.utc).isoformat(),
    'features': features,
}, ensure_ascii=False, separators=(',', ':')) + '\n')
print('Saved', len(features), 'features; runways:', sorted(runways))
