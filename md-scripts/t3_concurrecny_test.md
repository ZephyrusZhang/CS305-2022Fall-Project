clear ports and run simulator
```bash
kill -9 $(lsof -i:12345|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48001|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48002|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48003|awk '{print $2}'|tail -n 1)
cd ..
clear
pwd
perl util/hupsim.pl -m test/tmp3/topo3.map -n test/tmp3/nodes3.map -p 12345 -v 3
```
run peer 1
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp3/nodes3.map -c test/tmp3/data3-1.fragment -m 100 -i 1 -t 60
```
```
DOWNLOAD test/tmp3/download_target3.chunkhash test/tmp3/download_result.fragment
```
run peer 2
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp3/nodes3.map -c test/tmp3/data3-2.fragment -m 100 -i 2 -t 60
```
run peer 3
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp3/nodes3.map -c test/tmp3/data3-3.fragment -m 100 -i 3 -t 60
```
