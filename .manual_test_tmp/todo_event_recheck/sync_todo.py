import json
import os
import sys
_ = json.load(sys.stdin)
mode = os.environ.get('TEST_ACK_MODE', '')
if mode == 'no_id':
    print(json.dumps({'ok': True, 'action': 'noop'}, ensure_ascii=False))
elif mode == 'late_bind':
    print(json.dumps({'ok': True, 'action': 'updated', 'external_id': 'EXT-LATE', 'integration_id': 'wrong-id'}, ensure_ascii=False))