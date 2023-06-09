#!/bin/sh

pdoc -o docs src/clev2er  --logo "https://www.homepages.ucl.ac.uk/~ucasamu/mssl_logo.png" --docformat google

git add docs

exit 0
