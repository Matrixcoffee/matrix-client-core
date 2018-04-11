# Matrix Client Core
[Matrix Client Core](https://github.com/Matrixcoffee/matrix-client-core) is a
featureful base platform that you can build wafer-thin (<10LOC if you want)
[Matrix](https://matrix.org) clients and/or bots on top of.

## Why does it exist?
It seems I like writing bots, and this core extracts nearly all of the things
they have in common into a single package, so I don't have to keep copying and
pasting all the same code to create a new bot. Also improvements made here will
benefit all bots instantly, rather than different improvements living in
different repositories, to be copypasta'd around to the other bots some day.

Oh, by the way, if you thought this looked surprisingly similar to my
[UnRedactBot](https://github.com/Matrixcoffee/UnRedactBot) project, you would
be right.

## Status
**Alpha**. (It works. Probably fairly well. But hasn't seen enough testing to
be higher than alpha, yet. It might still change in ways that break all things
built on top of it.)

## Recommended Installation
```
$ cd $SOME_EMPTY_DIR
$ git clone https://github.com/matrix-org/matrix-python-sdk.git
$ git clone https://github.com/Matrixcoffee/urllib-requests-adapter.git
$ wget -P urllib-requests-adapter https://github.com/Anorov/PySocks/raw/master/socks.py # (optional)
$ git clone https://github.com/Matrixcoffee/matrix-client-core.git
```
Taking it for a spin:
```
$ cd matrix-client-core
$ /bin/sh testclient.sh
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
