echo -n -e "\033]0;Peer4\007"
cd $(dirname "$0")/../..
export SIMULATOR="127.0.0.1:12345"
clear
# 4 4bec20891a68887eef982e9cda5d02ca8e6d4f57
python3 src/peer.py -p example/ex_nodes_map -c example/data4.fragment -m 1 -i 4 -v 2