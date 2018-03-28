# UnRedactBot
UnRedactBot is a [Matrix](https://matrix.org) bot that listens for redaction events, and re-publishes the redacted content

## Why does it exist?
UnRedactBot is mainly a toy, but it has an important point to prove. This point
is that redaction events stand out like a sore thumb at the protocol level,
highlighting potentially interesting messages to malicious agents.

UnRedactBot helps to demonstrate this by making redacted messages stand out
like a sore thumb in regular clients as well. The fact that users respond
negatively to UnRedactBot's operation seems to underscore the need for this
message to be taught. UnRedactBot doesn't fabricate things out of thin air. It
merely shows and highlights what's already there. Just because regular clients
muffle redacted events away, doesn't mean they're really gone.

Whatever your purpose in running UnRedactBot, if you use it in public, please
be responsible and let people know that content will be UnRedact-ed, e.g. by
adding it to the room's topic. UnRedactBot will also help let people know it's
watching by posting its read receipt on every message it stores.

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

UnRedactBot does not know how to register an account, so you will need to
create it by other means. [Riot.im](https://riot.im/app), for example.

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
