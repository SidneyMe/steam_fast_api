from datetime import datetime, timedelta
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import status


class RequestLimiter(BaseHTTPMiddleware):

    def __init__(self,
                 app,
                 dispatch = None,
                 max_calls: int = 100,
                 time_window: int = 10):
        super().__init__(app, dispatch)
        self.max_calls = max_calls
        self.time_window = time_window
        self.call_track = defaultdict(dict)

    def new_client(self, client_ip: str):
        first_request = datetime.now()
        self.call_track[client_ip]['remaining'] = self.max_calls
        self.call_track[client_ip]['first_request'] = first_request

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        client_ip = request.client.host
        
        if client_ip not in self.call_track:
            self.new_client(client_ip)

        client = self.call_track[client_ip]
        request_time = datetime.now()
        request_diff: timedelta = request_time - client['first_request']

        if request_diff.total_seconds() > self.time_window:
            self.new_client(client_ip)
            client = self.call_track[client_ip]

        else:
            if client['remaining'] <= 0:
                time_to_wait = self.time_window - request_diff.total_seconds()
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={'msg': f"You will be able to use this api in {time_to_wait:.2f} secs"}
                )

        client['remaining'] -= 1
        return await call_next(request)