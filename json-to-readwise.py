#!/usr/bin/env python3

import os
import fileinput
from urllib.request import urlopen, Request

token = os.environ['READWISE_TOKEN']
user_agent = os.environ['USER_AGENT']
content = '{{"highlights":{}}}'.format("".join(fileinput.input(encoding='utf-8')))

req = Request(
    'https://readwise.io/api/v2/highlights/',
    headers={
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': user_agent
    },
    data=content.encode('utf-8'),
    method='POST',
)
urlopen(req)
