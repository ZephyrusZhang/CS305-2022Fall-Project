echo -n -e "\033]0;2\007"
cd $(dirname "$0")/../..
export SIMULATOR="127.0.0.1:12345"
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-2.fragment -m 100 -i 2
#DOWNLOAD test/tmp5/targets/download.chunkhash test/tmp5/results/result3.fragment