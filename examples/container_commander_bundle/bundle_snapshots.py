#!/usr/bin/env python3
from datetime import datetime, timezone
import io
import os
import tarfile

import bundle_common
import bundle_docker
from bundle_common import error_result, is_not_found


def list_snapshots(volume_name=""):
    if not os.path.exists(bundle_common.SNAPSHOT_DIR):
        return {"snapshots": []}
    result = []
    for filename in sorted(os.listdir(bundle_common.SNAPSHOT_DIR), reverse=True):
        if not filename.endswith(".tar.gz"):
            continue
        if volume_name and not filename.startswith(volume_name):
            continue
        filepath = os.path.join(bundle_common.SNAPSHOT_DIR, filename)
        stat = os.stat(filepath)
        result.append(
            {
                "filename": filename,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    return {"snapshots": result}


def delete_snapshot(filename):
    filepath = os.path.join(bundle_common.SNAPSHOT_DIR, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return {"deleted": True, "filename": filename}
        return {"deleted": False, "filename": filename}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def create_snapshot(volume_name, tag=""):
    try:
        client = bundle_docker.get_docker_client()
        try:
            client.volumes.get(volume_name)
        except Exception as exc:
            if is_not_found(exc):
                return {"created": False, "filename": "", "volume": volume_name}
            return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        tag_part = f"_{tag}" if tag else ""
        filename = f"{volume_name}{tag_part}_{ts}.tar.gz"
        filepath = os.path.join(bundle_common.SNAPSHOT_DIR, filename)
        os.makedirs(bundle_common.SNAPSHOT_DIR, exist_ok=True)

        container = None
        try:
            container = client.containers.run(
                "alpine:latest",
                command="sh -c 'mkdir -p /backup && tar czf /backup/snapshot.tar.gz -C /workspace .'",
                volumes={volume_name: {"bind": "/workspace", "mode": "ro"}},
                detach=True,
                remove=False,
                labels={"trion.managed": "true", "trion.temp": "snapshot"},
            )
            result = container.wait(timeout=120)
            exit_code = result.get("StatusCode", -1) if isinstance(result, dict) else -1
            if int(exit_code) != 0:
                return {"created": False, "filename": "", "volume": volume_name}

            bits, _stat = container.get_archive("/backup/snapshot.tar.gz")
            raw = b"".join(bits)
            outer_tar = tarfile.open(fileobj=io.BytesIO(raw), mode="r")
            members = outer_tar.getmembers()
            if not members:
                return {"created": False, "filename": "", "volume": volume_name}
            inner_file = outer_tar.extractfile(members[0])
            if inner_file is None:
                return {"created": False, "filename": "", "volume": volume_name}
            with open(filepath, "wb") as handle:
                handle.write(inner_file.read())
            return {"created": True, "filename": filename, "volume": volume_name}
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def restore_snapshot(snapshot_filename, target_volume=""):
    try:
        client = bundle_docker.get_docker_client()
        filepath = os.path.join(bundle_common.SNAPSHOT_DIR, snapshot_filename)
        if not os.path.exists(filepath):
            return {"restored": False, "volume": "", "filename": snapshot_filename}

        volume_name = str(target_volume or "").strip()
        if not volume_name:
            base = snapshot_filename.rsplit("_", 2)[0] if "_" in snapshot_filename else "restored"
            ts = str(int(datetime.now(timezone.utc).timestamp()))
            volume_name = f"{base}_restored_{ts}"

        try:
            client.volumes.get(volume_name)
        except Exception as exc:
            if is_not_found(exc):
                client.volumes.create(
                    name=volume_name,
                    driver="local",
                    labels={
                        "trion.managed": "true",
                        "trion.restored_from": snapshot_filename,
                        "trion.created": datetime.now(timezone.utc).isoformat(),
                    },
                )
            else:
                return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)

        container = None
        try:
            container = client.containers.create(
                "alpine:latest",
                command="tar xzf /backup/snapshot.tar.gz -C /workspace",
                volumes={volume_name: {"bind": "/workspace", "mode": "rw"}},
                labels={"trion.managed": "true", "trion.temp": "restore"},
            )
            with open(filepath, "rb") as handle:
                tar_data = handle.read()

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                info = tarfile.TarInfo(name="snapshot.tar.gz")
                info.size = len(tar_data)
                tar.addfile(info, io.BytesIO(tar_data))
            tar_stream.seek(0)

            container.put_archive("/backup", tar_stream.read())
            container.start()
            result = container.wait(timeout=120)
            exit_code = result.get("StatusCode", -1) if isinstance(result, dict) else -1
            if int(exit_code) != 0:
                return {"restored": False, "volume": "", "filename": snapshot_filename}
            return {"restored": True, "volume": volume_name, "filename": snapshot_filename}
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)
