#!/bin/sh

PYTHONFLAGS=

while [ "$1" ]; do case "$1" in
	-i)	PYTHONFLAGS="$PYTHONFLAGS $1"
		shift
		;;
	--)	shift
		break
		;;
	*)	break
		;;
esac; done

PYTHONPATH=.:../urllib-requests-adapter:../matrix-python-sdk python3 $PYTHONFLAGS TestClient.py "$@"
