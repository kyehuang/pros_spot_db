# pros_spot_db

This project provides a PostgreSQL database for managing Spot robot graph data, including node positions, orientations, and directional connections. It supports asynchronous access and bulk operations via Python and Docker.

## 🚀 Quick Start

Use Docker Compose to spin up the PostgreSQL environment:

```bash
docker-compose up -d
```

The database will start in the background with the following default settings:

- Host: `localhost`
- Port: `5432`
- User: `myuser`
- Password: `mypassword`
- Database: `mydatabase`

## 🗃️ Table Structure

By default, the database includes a single main table:

### `nodes`

Stores the robot's spatial position, rotation, joint angles, and directional links.

**Key columns:**

- Position: `x`, `y`, `z`
- Rotation: `rx`, `ry`, `rz`
- Joint angles: `joint_angle` (as JSON)
- Directional links:  
  `up_node_id`, `down_node_id`, `left_node_id`, `right_node_id`,  
  `front_node_id`, `back_node_id`,  
  `rx_plus_node_id`, `rx_minus_node_id`,  
  `ry_plus_node_id`, `ry_minus_node_id`,  
  `rz_plus_node_id`, `rz_minus_node_id`

A unique constraint is enforced on the combination of  
`(x, y, z, rx, ry, rz)` to avoid duplicate nodes.

## 🐍 Python Usage

You can use the `AsyncSpotGraphDB` class to interact with the database:

```python
from spot_graph import AsyncSpotGraphDB, SpotNode

db = AsyncSpotGraphDB("postgresql+asyncpg://myuser:mypassword@localhost:5432/mydatabase")
await db.create_tables()

node = SpotNode([0, 0, 0.2], [0, 0, 0])
await db.add_node(node)
```

Bulk insert and directional link updates are supported for high performance.

## 💾 Database Backup

To create a backup using `pg_dump`:

```bash
pg_dump -U myuser -h localhost -d mydatabase -f backup.sql
```

## 📁 Project Structure

```
.
├── docker-compose.yml         # PostgreSQL service definition
├── spot_graph.py              # Async DB access logic
├── backup.sql                 # Backup file (optional)
└── README.md
```

## 📌 Notes

- This setup is optimized for Spot-like robot state graph traversal and storage.
- All operations are asynchronous (via SQLAlchemy + asyncpg).

## 🐳 Backup and Restore from Docker

If your PostgreSQL database is running inside a Docker container, use the following commands.

### 📤 Export (Backup) from Docker container

```bash
docker exec -t <container_name> pg_dump -U myuser -d mydatabase > backup.sql
```

Example:

```bash
docker exec -t pros_spot_db-db-1 pg_dump -U myuser -d mydatabase > backup.sql
```

### 📥 Import (Restore) into Docker container

```bash
cat backup.sql | docker exec -i <container_name> psql -U myuser -d mydatabase
```

Example:

```bash
cat backup.sql | docker exec -i pros_spot_db-db-1 psql -U myuser -d mydatabase
```

> Tip: Use `docker compose ps` to find your actual container name if you're using Docker Compose.