#!/usr/bin/env python3

import utils
import fileinput
import json

highlights = json.loads("".join(fileinput.input(encoding='utf-8')))

utils.create_highlights(highlights)
