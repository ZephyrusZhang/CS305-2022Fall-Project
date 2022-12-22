echo -n -e "\033]0;Peer1\007"
cd $(dirname "$0")/../..
export SIMULATOR="127.0.0.1:12345"
clear
#1 12e3340d8b1a692c6580c897c0e26bd1ac0eaadf
python3 src/peer.py -p example/ex_nodes_map -c example/data1.fragment -m 1 -i 1 -v 3