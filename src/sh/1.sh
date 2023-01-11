echo -n -e "\033]0;1\007"
cd $(dirname "$0")/../..
pwd
export SIMULATOR="127.0.0.1:12345"
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-1.fragment -m 100 -i 1
#DOWNLOAD test/tmp5/targets/target1.chunkhash test/tmp5/results/result1.fragment