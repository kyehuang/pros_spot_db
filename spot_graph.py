import asyncio
import json
import time
import dataclasses
from tqdm import tqdm

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import (
    Column, Integer, Float, Text, ForeignKey, UniqueConstraint, select
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import insert

Base = declarative_base()

@dataclasses.dataclass
class Node(Base):
    """
    A class representing a node in the graph.
    """
    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    rx = Column(Float, nullable=False)
    ry = Column(Float, nullable=False)
    rz = Column(Float, nullable=False)
    joint_angle = Column(Text)
    is_visited = Column(Integer)

    up_node_id = Column(Integer, ForeignKey('nodes.id'))
    down_node_id = Column(Integer, ForeignKey('nodes.id'))
    left_node_id = Column(Integer, ForeignKey('nodes.id'))
    right_node_id = Column(Integer, ForeignKey('nodes.id'))
    front_node_id = Column(Integer, ForeignKey('nodes.id'))
    back_node_id = Column(Integer, ForeignKey('nodes.id'))
    rx_plus_node_id = Column(Integer, ForeignKey('nodes.id'))
    rx_minus_node_id = Column(Integer, ForeignKey('nodes.id'))
    ry_plus_node_id = Column(Integer, ForeignKey('nodes.id'))
    ry_minus_node_id = Column(Integer, ForeignKey('nodes.id'))
    rz_plus_node_id = Column(Integer, ForeignKey('nodes.id'))
    rz_minus_node_id = Column(Integer, ForeignKey('nodes.id'))

    __table_args__ = (
        UniqueConstraint('x', 'y', 'z', 'rx', 'ry', 'rz', name='uq_nodes_position_rotation'),
    )

class AsyncSpotGraphDB:
    """ 
    A class representing a database for the Spot robot's graph.
    """
    def __init__(self, db_url="postgresql+asyncpg://myuser:mypassword@localhost:5432/mydatabase"):
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def create_tables(self):
        """
        Create the database tables if they do not exist.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def add_node(self, node):
        """
        Add a node to the database.
        """
        async with self.async_session() as session:
            async with session.begin():
                stmt = insert(Node).values(
                    x=node.base_position[0],
                    y=node.base_position[1],
                    z=node.base_position[2],
                    rx=node.base_rotation[0],
                    ry=node.base_rotation[1],
                    rz=node.base_rotation[2],
                    joint_angle=json.dumps(node.joint_angle),
                    is_visited=int(node.is_visited)
                ).on_conflict_do_nothing(
                    index_elements=["x", "y", "z", "rx", "ry", "rz"]
                )
                await session.execute(stmt)
            await session.commit()

    async def bulk_add_nodes(self, nodes, batch_size=500):
        """
        Add a batch of nodes to the database.
        """
        key_to_id = {}

        async with self.async_session() as session:
            for i in tqdm(range(0, len(nodes), batch_size), desc="Inserting nodes"):
                batch = nodes[i:i+batch_size]
                stmt = insert(Node).values([
                    {
                        "x": node.base_position[0],
                        "y": node.base_position[1],
                        "z": node.base_position[2],
                        "rx": node.base_rotation[0],
                        "ry": node.base_rotation[1],
                        "rz": node.base_rotation[2],
                        "joint_angle": json.dumps(node.joint_angle),
                        "is_visited": int(node.is_visited)
                    }
                    for node in batch
                ]).on_conflict_do_nothing(
                    index_elements=["x", "y", "z", "rx", "ry", "rz"]
                ).returning(Node.id, Node.x, Node.y, Node.z, Node.rx, Node.ry, Node.rz)

                result = await session.execute(stmt)
                inserted = result.fetchall()

                for row in inserted:
                    key = (
                        round(row.x, 3), round(row.y, 3), round(row.z, 3),
                        round(row.rx, 3), round(row.ry, 3), round(row.rz, 3)
                    )
                    key_to_id[key] = row.id

            await session.commit()

        async with self.async_session() as session:
            for node in nodes:
                key = (
                    round(node.base_position[0], 3),
                    round(node.base_position[1], 3),
                    round(node.base_position[2], 3),
                    round(node.base_rotation[0], 3),
                    round(node.base_rotation[1], 3),
                    round(node.base_rotation[2], 3)
                )
                if key not in key_to_id:
                    stmt = select(Node.id).where(
                        (Node.x == key[0]) & (Node.y == key[1]) & (Node.z == key[2]) &
                        (Node.rx == key[3]) & (Node.ry == key[4]) & (Node.rz == key[5])
                    )
                    result = await session.execute(stmt)
                    node_id = result.scalar()
                    key_to_id[key] = node_id

        return key_to_id

    async def update_direction_link(self, from_id, to_id, direction):
        """
        Update the direction link between two nodes in the database.
        """
        valid_directions = {
            "up", "down", "left", "right", "front", "back",
            "rx_plus", "rx_minus", "ry_plus", "ry_minus", "rz_plus", "rz_minus"
        }
        if direction not in valid_directions:
            raise ValueError(f"Invalid direction: {direction}")

        async with self.async_session() as session:
            async with session.begin():
                node = await session.get(Node, from_id)
                setattr(node, f"{direction}_node_id", to_id)
            await session.commit()

    async def bulk_update_direction_links(self,
                updates: list[tuple[int, int, str]], batch_size=500):
        """
        Add a batch of direction links to the database.
        """
        valid_directions = {
            "up", "down", "left", "right", "front", "back",
            "rx_plus", "rx_minus", "ry_plus", "ry_minus", "rz_plus", "rz_minus"
        }

        async with self.async_session() as session:
            for i in tqdm(range(0, len(updates), batch_size), desc="Updating direction links"):
                batch = updates[i:i+batch_size]
                async with session.begin():
                    for from_id, to_id, direction in batch:
                        if direction not in valid_directions:
                            raise ValueError(f"Invalid direction: {direction}")

                        stmt = (
                            Node.__table__.update()
                            .where(Node.id == from_id)
                            .values({f"{direction}_node_id": to_id})
                        )
                        await session.execute(stmt)

    async def get_direction_neighbors(self, node_id):
        """
        Get the neighbors of a node in the graph.
        """
        async with self.async_session() as session:
            node = await session.get(Node, node_id)
            if node:
                return {
                    "up": node.up_node_id, "down": node.down_node_id,
                    "left": node.left_node_id, "right": node.right_node_id,
                    "front": node.front_node_id, "back": node.back_node_id,
                    "rx_plus": node.rx_plus_node_id, "rx_minus": node.rx_minus_node_id,
                    "ry_plus": node.ry_plus_node_id, "ry_minus": node.ry_minus_node_id,
                    "rz_plus": node.rz_plus_node_id, "rz_minus": node.rz_minus_node_id
                }
            return {}

    async def close(self):
        """
        Close the database connection.
        """
        await self.engine.dispose()

    async def get_node_id(self, base_position, base_rotation):
        """
        Get the node ID from the database based on the position and rotation of the Spot robot.
        """
        async with self.async_session() as session:
            stmt = select(Node.id).where(
                (Node.x == base_position[0]) &
                (Node.y == base_position[1]) &
                (Node.z == base_position[2]) &
                (Node.rx == base_rotation[0]) &
                (Node.ry == base_rotation[1]) &
                (Node.rz == base_rotation[2])
            )
            result = await session.execute(stmt)
            return result.scalar()

    async def get_all_node_keys(self):
        """
        Get all node keys from the database.
        """
        async with self.async_session() as session:
            stmt = select(Node.id, Node.x, Node.y, Node.z, Node.rx, Node.ry, Node.rz)
            result = await session.execute(stmt)
            rows = result.fetchall()
            return {
                (round(row.x, 3), round(row.y, 3), round(row.z, 3),
                 round(row.rx, 3), round(row.ry, 3), round(row.rz, 3)): row.id
                for row in rows
            }

class SpotNode:
    """
    A class representing a node in the Spot robot's graph.
    """
    def __init__(self, base_position, base_rotation):
        self.base_position = base_position
        self.base_rotation = base_rotation
        self.joint_angle = [0] * 12
        self.is_visited = False

async def main():
    """
    Main function to demonstrate the usage of the AsyncSpotGraphDB class.
    """
    db = AsyncSpotGraphDB("postgresql+asyncpg://myuser:mypassword@localhost:5432/mydatabase")
    await db.create_tables()

    node_a = SpotNode([0, 0, 0], [0, 0, 0])
    node_b = SpotNode([2, 0, 0], [0, 0, 0])
    node_c = SpotNode([1, 3, 2], [0, 0, 0])

    await db.add_node(node_a)
    await db.add_node(node_b)
    await db.add_node(node_c)

    await db.update_direction_link(1, 2, "right")
    await db.update_direction_link(1, 3, "front")

    neighbors = await db.get_direction_neighbors(1)
    print("Neighbors of node A:", neighbors)

    node_list = [SpotNode([i, i, i], [i, i, 0]) for i in range(20000)]
    start = time.perf_counter()
    await db.bulk_add_nodes(node_list)
    end = time.perf_counter()

    print(f"Added 20000 nodes in {end - start:.2f} seconds")
    print(f"{20000 / (end - start):.2f} node/s")

    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
