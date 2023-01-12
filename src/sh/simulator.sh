echo -n -e "\033]0;Simulator\007"
cd $(dirname "$0")/../..
clear
perl util/hupsim.pl -m example/ex_topo.map -n example/ex_nodes_map -p 12345 -v 2
