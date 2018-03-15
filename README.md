# UnRedactBot
UnRedactBot is a Matrix bot that listens for redaction events, and re-publishes the redacted content

## Why does it exist?
This is mainly a toy, but it might come in handy if you really believe people
shouldn't be allowed to redact their own messages. If you use it, please be
responsible and let people know that content will be UnRedact-ed, e.g. by
adding it to the room's topic.

## Status
**Alpha**. (It works. Probably fairly well. No rate-limiting though. And it
really hasn't seen enough testing to be anything but alpha.)

## Recommended Installation
```
$ cd $SOME_EMPTY_DIR
$ git clone https://github.com/matrix-org/matrix-python-sdk.git
$ git clone https://github.com/Matrixcoffee/urllib-requests-adapter.git
$ wget -P urllib-requests-adapter https://github.com/Anorov/PySocks/raw/master/socks.py # (optional)
$ git clone https://github.com/Matrixcoffee/UnRedactBot.git
```
Running it:
```
$ cd UnRedactBot
$ /bin/sh unredactbot.sh
```

Happy hacking!

## License
Copyright 2018 @Coffee:matrix.org

   > Licensed under the Apache License, Version 2.0 (the "License");
   > you may not use this file except in compliance with the License.

   > The full text of the License can be obtained from the file called [LICENSE](LICENSE).

   > Unless required by applicable law or agreed to in writing, software
   > distributed under the License is distributed on an "AS IS" BASIS,
   > WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   > See the License for the specific language governing permissions and
   > limitations under the License.
