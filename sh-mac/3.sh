echo -n -e "\033]0;Peer3\007"
cd $(dirname "$0")/..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p example/ex_nodes_map -c example/data3.fragment -m 1 -i 3 -v 2