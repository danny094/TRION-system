from pathlib import Path
import sqlite3
import sys


SERVER_DIR = Path(__file__).resolve().parents[1] / "mcp-servers" / "container-commander"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))


def _init_blueprint_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE blueprints (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                dockerfile TEXT DEFAULT '',
                image TEXT DEFAULT '',
                runtime TEXT DEFAULT '',
                ports_json TEXT DEFAULT '[]',
                mounts_json TEXT DEFAULT '[]',
                environment_json TEXT DEFAULT '{}',
                resources_json TEXT DEFAULT '{}',
                tags_json TEXT DEFAULT '[]',
                icon TEXT DEFAULT '📦',
                created_at TEXT,
                updated_at TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO blueprints (
                id, name, description, dockerfile, image, runtime, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("demo", "Demo", "Example blueprint", "FROM python:3.12", "python:3.12", "docker", "2026-05-15T10:00:00Z", "2026-05-15T11:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()


class _FakeContainer:
    def __init__(self, *, status="exited", managed=True, protected=False, cid="c1", name="demo", labels=None, manifest=None):
        self.id = cid
        self.name = name
        self.status = status
        self.labels = dict(labels or {})
        if managed and "trion.managed" not in self.labels:
            self.labels["trion.managed"] = "true"
        if protected and "trion.protected" not in self.labels:
            self.labels["trion.protected"] = "true"
        self.attrs = {
            "Config": {"Image": "demo:latest"},
            "Created": "2026-05-15T10:00:00Z",
            "State": {"Status": status, "Running": status == "running"},
            "NetworkSettings": {
                "Networks": {"bridge": {"IPAddress": "172.18.0.12"}},
                "Ports": {"8080/tcp": [{"HostPort": "18080", "HostIp": "127.0.0.1"}]},
            },
        }
        self.started = False
        self.stopped = False
        self._manifest = manifest

    def reload(self):
        self.attrs["State"]["Status"] = self.status
        self.attrs["State"]["Running"] = self.status == "running"

    def start(self):
        self.started = True
        self.status = "running"

    def stop(self, timeout=10):
        self.stopped = True
        self.status = "exited"

    def remove(self, force=True):
        self.removed = True

    def exec_run(self, args, demux=False, workdir=None):
        class _Result:
            def __init__(self, exit_code, output):
                self.exit_code = exit_code
                self.output = output

        if demux:
            if "pwd" in str(args or ""):
                return _Result(0, (b"/workspace\n", b""))
            return _Result(0, (b"ok\n", b""))
        if self._manifest is None:
            return _Result(1, b"")
        return _Result(0, self._manifest.encode("utf-8"))

    def stats(self, stream=False):
        return {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 2_000_000_000},
                "system_cpu_usage": 20_000_000_000,
                "online_cpus": 4,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 1_000_000_000},
                "system_cpu_usage": 10_000_000_000,
            },
            "memory_stats": {"usage": 256 * 1024 * 1024, "limit": 1024 * 1024 * 1024},
            "networks": {"bridge": {"rx_bytes": 1234, "tx_bytes": 5678}},
        }


class _FakeClient:
    def __init__(self, container, networks=None):
        self.containers = self
        self._container = container
        self.networks = _FakeNetworks(networks or [])

    def get(self, container_id):
        return self._container


class _FakeNetwork:
    def __init__(self, name="trion-sandbox", short_id="net1", labels=None, internal=True, driver="bridge", containers=None):
        self.name = name
        self.short_id = short_id
        self.removed = False
        self.attrs = {
            "Labels": dict(labels or {"trion.managed": "true", "trion.network.type": "internal"}),
            "Internal": internal,
            "Driver": driver,
            "Containers": dict(containers or {}),
        }

    def remove(self):
        self.removed = True


class _FakeNetworks:
    def __init__(self, networks):
        self._networks = {network.name: network for network in networks}

    def list(self, filters=None):
        return list(self._networks.values())

    def get(self, name):
        if name not in self._networks:
            raise type("NotFound", (Exception,), {})()
        return self._networks[name]


class _FakeVolume:
    def __init__(self, name="trion_ws_demo_1", labels=None, created_at="2026-05-15T10:00:00Z", driver="local", mountpoint="/var/lib/docker/volumes/demo"):
        self.name = name
        self.attrs = {
            "Labels": dict(labels or {"trion.managed": "true", "trion.blueprint": "demo", "trion.created": created_at}),
            "CreatedAt": created_at,
            "Driver": driver,
            "Mountpoint": mountpoint,
        }
        self.removed = False

    def remove(self, force=False):
        self.removed = True


class _FakeVolumes:
    def __init__(self, volumes):
        self._volumes = {volume.name: volume for volume in volumes}

    def list(self, filters=None):
        return list(self._volumes.values())

    def get(self, volume_name):
        if volume_name not in self._volumes:
            raise type("NotFound", (Exception,), {})()
        return self._volumes[volume_name]
