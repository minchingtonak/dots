#!/bin/bash
set -Eeuxo pipefail

while IFS="" read -r p || [ -n "$p" ]
do
  code --install-extension "$p"
done < extensions