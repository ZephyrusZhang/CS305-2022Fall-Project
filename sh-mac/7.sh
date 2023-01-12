echo -n -e "\033]0;Peer7\007"
cd $(dirname "$0")/..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-7.fragment -m 100 -i 12