# clear terminal
osascript -e 'tell application "terminal"
    close every window
end tell'
# clear socket port bonding
kill -9 $(lsof -i:12345|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48001|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48002|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48003|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48004|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48005|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48006|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48007|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48008|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48009|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:480010|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:480011|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:480012|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:480013|awk '{print $2}'|tail -n 1)
# run simulator
open -a terminal.app $(dirname "$0")/simulator.sh
# prepare data for peers
cd ..
python3 util/make_data.py example/ex_file.tar ./example/data1.fragment 4 1
python3 util/make_data.py example/ex_file.tar ./example/data2.fragment 4 2
python3 util/make_data.py example/ex_file.tar ./example/data3.fragment 4 3
python3 util/make_data.py example/ex_file.tar ./example/data4.fragment 4 4
# run peers
open -a terminal.app $(dirname "$0")/1.sh
open -a terminal.app $(dirname "$0")/2.sh
open -a terminal.app $(dirname "$0")/3.sh
open -a terminal.app $(dirname "$0")/4.sh