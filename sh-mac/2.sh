echo -n -e "\033]0;Peer2\007"
cd $(dirname "$0")/..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p example/ex_nodes_map -c example/data2.fragment -m 1 -i 2 -v 2