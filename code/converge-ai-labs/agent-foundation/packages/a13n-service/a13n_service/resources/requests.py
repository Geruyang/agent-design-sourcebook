"""The assembled runtime as one typed FastAPI dependency for resource routes."""

from typing import Annotated

from fastapi import Depends, Request

from a13n_service.resources.runtime import Runtime


async def current_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


CurrentRuntime = Annotated[Runtime, Depends(current_runtime)]
