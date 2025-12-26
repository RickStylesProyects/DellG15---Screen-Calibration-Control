#!/bin/bash
# Find the latest generated profile
LATEST_PROFILE=$(ls -t ~/.local/share/icc/custom_saturation_*.icc | head -n 1)
echo "Checking profile: $LATEST_PROFILE"
if [ -f "$LATEST_PROFILE" ]; then
    iccdump "$LATEST_PROFILE" | head -n 20
else
    echo "No profile found."
fi
