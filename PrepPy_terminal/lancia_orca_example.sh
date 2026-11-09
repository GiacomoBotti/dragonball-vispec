EXE="orca"

filein=(*.inp)
fileout="${filein[0]%.inp}.out"

$EXE ${filein[0]} > ${fileout}

#mkdir -p $WD/$SLURM_JOBID
cp ./* $WD

if [ "$status" -eq 0 ]; then
    cd /work/gbotti || exit 1
    rm -rf "$SCRDIR"
else
    echo "ORCA failed with exit status $status"
    echo "Scratch directory preserved: $SCRDIR"
fi

exit "$status"

