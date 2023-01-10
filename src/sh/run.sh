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
# create file
cd $(dirname "$0")/../..
python3 util/make_data.py example/ex_file.tar ./example/data1.fragment 4 1
python3 util/make_data.py example/ex_file.tar ./example/data2.fragment 4 2
python3 util/make_data.py example/ex_file.tar ./example/data3.fragment 4 3
python3 util/make_data.py example/ex_file.tar ./example/data4.fragment 4 4
sed -n "2,4p" master.chunkhash > example/download.chunkhash
# run simulator
open -a terminal.app $(dirname "$0")/simulator.sh
# run peers
open -a terminal.app $(dirname "$0")/peer1.sh
open -a terminal.app $(dirname "$0")/peer2.sh
# open -a terminal.app $(dirname "$0")/peer3.sh
# open -a terminal.app $(dirname "$0")/peer4.sh