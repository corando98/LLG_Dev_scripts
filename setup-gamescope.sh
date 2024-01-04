#!/usr/bin/bash

# Default values
TARGET_WIDTH=1920
TARGET_HEIGHT=1200
OUTPUT_WIDTH=2560
OUTPUT_HEIGHT=1600
REFRESH_RATE=144

# Usage function
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -t <target width>     Target resolution width for downscaling (default: $TARGET_WIDTH)"
    echo "  -T <target height>    Target resolution height for downscaling (default: $TARGET_HEIGHT)"
    echo "  -o <output width>     Output resolution width (default: $OUTPUT_WIDTH)"
    echo "  -O <output height>    Output resolution height (default: $OUTPUT_HEIGHT)"
    echo "  -r <refresh rate>     Refresh rate (default: $REFRESH_RATE)"
    echo ""
    echo "Example: $0 -t 1920 -T 1200 -o 2560 -O 1600 -r 144"
    echo "If no options are specified, default values will be used."
    exit 1
}

# Parse command-line arguments
while getopts t:T:o:O:r:h flag
do
    case "${flag}" in
        t) TARGET_WIDTH=${OPTARG};;
        T) TARGET_HEIGHT=${OPTARG};;
        o) OUTPUT_WIDTH=${OPTARG};;
        O) OUTPUT_HEIGHT=${OPTARG};;
        r) REFRESH_RATE=${OPTARG};;
        h) usage;;
        *) usage;;
    esac
done

# Configuration file path
CONFIG_DIR="$HOME/.config/environment.d"
CONFIG_FILE="$CONFIG_DIR/override-gamescopecmd.conf"

# Create configuration directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Write the configuration
echo "Creating Gamescope configuration with the following settings:"
echo "  Target Resolution: $TARGET_WIDTH x $TARGET_HEIGHT"
echo "  Output Resolution: $OUTPUT_WIDTH x $OUTPUT_HEIGHT"
echo "  Refresh Rate: $REFRESH_RATE Hz"

cat <<EOF > "$CONFIG_FILE"
export GAMESCOPECMD="\$GAMESCOPECMD -w $TARGET_WIDTH -h $TARGET_HEIGHT -W $OUTPUT_WIDTH -H $OUTPUT_HEIGHT -S integer -r $REFRESH_RATE "
export STEAM_DISPLAY_REFRESH_LIMITS="60,$REFRESH_RATE"
EOF

echo "Configuration created. Please restart Steam Game Mode to see changes."
