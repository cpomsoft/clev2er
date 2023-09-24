#!/bin/sh

pdoc -o docs src/clev2er --no-include-undocumented --mermaid --logo "https://www.homepages.ucl.ac.uk/~ucasamu/mssl_logo.png" --docformat google 
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "pdoc failed"
    exit 1
fi
git add docs

exit 0
