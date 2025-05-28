# OpenLR Decoder for QGIS

A QGIS plugin to decode and visualize OpenLR location references on a custom road network stored in PostgreSQL/PostGIS.

This plugin provides a simple GUI to input OpenLR strings, connect to your spatial database, and display the decoded road segments directly on the map.

---

## 🧭 Overview

OpenLR (Open Location Referencing) is a compact, map-agnostic way to encode geographic locations.

This plugin is a QGIS frontend for a previously implemented Python-based OpenLR decoder.  
While the original version was command-line only, this plugin brings OpenLR decoding directly into the QGIS interface.

---

## 🔧 Features

- Connect to a PostgreSQL/PostGIS database with a custom road network
- Input OpenLR-encoded strings from a simple dialog
- Automatically decode and display the result as a new layer (`Decoded OpenLR Lines`)
- GUI-based operation, no command-line interaction required

---

## 🛠 Requirements

- QGIS LTR 3.34 (Prizren) or newer
- PostgreSQL with PostGIS enabled
- Python packages (used internally):
  - `openlr-dereferencer`
  - `psycopg2`
  - `pyproj`

---

## 🗄 PostgreSQL Schema Requirements

Your road network must include the following tables:

### `roads` table

| Column    | Type             | Description                         |
| --------- | ---------------- | ----------------------------------- |
| id        | bigint           | Primary key                         |
| fow       | smallint         | Form of Way (OpenLR spec)           |
| frc       | smallint         | Functional Road Class (OpenLR spec) |
| flowdir   | smallint         | 1=both, 2=end→start, 3=start→end    |
| from_int  | bigint           | Starting intersection ID            |
| to_int    | bigint           | Ending intersection ID              |
| len       | double precision | Segment length (meters)             |
| geom      | LineString(4326) | Geometry (WGS84)                    |

### `intersections` table

| Column | Type        | Description          |
|--------|-------------|----------------------|
| id     | bigint      | Primary key          |
| geom   | Point(4326) | WGS84 point geometry |

---

## 🚀 Installation

1. Download or clone this repository.
2. Create a ZIP archive of the plugin directory (make sure it includes `__init__.py` and `metadata.txt`).
3. In QGIS, go to **Plugins > Install from ZIP** and select the archive.
4. Restart QGIS and launch the plugin from the toolbar.

---

## 📦 File Structure

openlr-qgis-plugin/
├── OpenLRDecoder.py # Main plugin logic
├── OpenLRDecoder_dialog.py # Dialog controller
├── OpenLRDecoder_dialog_base.ui # UI definition
├── __init__.py # QGIS plugin entry point
├── metadata.txt # Plugin metadata
└── README.md # This file


---

## 📝 Notes

- This plugin is derived from a Python CLI-based decoder implementation.
- For CLI-based testing or automation, refer to the original version using `myTest.py`.

---

## 📄 License

MIT License

---

## 🙋 Feedback

Feel free to open issues or pull requests for questions, suggestions, or improvements.