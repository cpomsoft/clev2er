#!/bin/sh

pdoc -o docs src/clev2er  --logo "http://www.cpom.ucl.ac.uk/downloads/mssl_logo.png" --docformat google
git add docs

exit 0
