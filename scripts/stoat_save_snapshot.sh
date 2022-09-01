#!/bin/bash

source $LATTE_PATH/.env/bin/activate
app_name=$1
stoat_path=$2
state=$3
RESULT_DIR="$LATTE_PATH/stoat_results"
TMP_SNAPSHOT=$RESULT_DIR/$app_name/tmp
echo $TMP_SNAPSHOT
rm -rf $TMP_SNAPSHOT/*
mkdir -p $TMP_SNAPSHOT/BASE
cp $stoat_path/$state.xml $TMP_SNAPSHOT/BASE/INITIAL.xml
cp $stoat_path/$state.png $TMP_SNAPSHOT/BASE/INITIAL.png
echo STRUCTURE > $TMP_SNAPSHOT/initiated.txt
python $LATTE_PATH/py_src/main.py --app-name "$app_name" --output-path "$RESULT_DIR"  --app-task "stoat_save_snapshot" --emulator  --debug



