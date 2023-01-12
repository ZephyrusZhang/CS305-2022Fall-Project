echo -n -e "\033]0;Simulator\007"
cd $(dirname "$0")/..
clear
mkdir test/tmp5/results
perl util/hupsim.pl -m test/tmp5/topo5.map -n test/tmp5/nodes5.map -p 12345 -v 3
