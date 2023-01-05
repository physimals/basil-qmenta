tag=`cat version.txt`

python test_sdk_tool.py martincraig/basil-qmenta:$tag ./test_input/ ./test_output/ --settings settings.json --values settings_values.json

