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
# run simulator
open -a terminal.app $(dirname "$0")/simulator.sh
# run peers
open -a terminal.app $(dirname "$0")/1.sh
open -a terminal.app $(dirname "$0")/2.sh
open -a terminal.app $(dirname "$0")/3.sh
open -a terminal.app $(dirname "$0")/4.sh
open -a terminal.app $(dirname "$0")/5.sh
open -a terminal.app $(dirname "$0")/6.sh
open -a terminal.app $(dirname "$0")/7.sh
open -a terminal.app $(dirname "$0")/8.sh