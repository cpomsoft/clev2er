#!/bin/sh

pdoc -o docs src/clev2er --no-include-undocumented --mermaid --logo "https://www.homepages.ucl.ac.uk/~ucasamu/mssl_logo.png" --docformat google 

git add docs

exit 0
