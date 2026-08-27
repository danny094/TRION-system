#!/usr/bin/env python3


def get_docker_client():
    try:
        from docker import from_env

        return from_env()
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc
