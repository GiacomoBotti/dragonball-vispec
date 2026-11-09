#!/bin/bash


if [ -z "$1" ]; then
    echo "Usage: $0 <ngeo>"
    exit 1
fi

ngeo=$1

echo "Number of geometries: $ngeo"
echo "Starting directory: $(pwd)"
echo "----------------------------------------"

for ((x=1; x<=ngeo; x++)); do
    echo "Processing geometry $x"

    (
        cd "geo${x}" || exit 1

        echo "Current directory: $(pwd)"
        echo "Submission script: lancia_orca.sh"

        if [ ! -f lancia_orca.sh ]; then
            echo "ERROR: lancia_orca.sh not found!"
            exit 1
        fi

        echo "Submitting job launch_${x}..."

        sbatch --job-name="launch_${x}" lancia_orca.sh
        status=$?

        echo "sbatch exit status: $status"
    )

    echo "----------------------------------------"
done
