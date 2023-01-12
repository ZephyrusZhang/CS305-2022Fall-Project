clear ports and run simulator
```bash
kill -9 $(lsof -i:12345|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48001|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48002|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48003|awk '{print $2}'|tail -n 1)
cd ..
clear
pwd
perl util/hupsim.pl -m test/tmp4/topo4.map -n test/tmp4/nodes4.map -p 12345 -v 3
```
run peer 1
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp4/nodes4.map -c test/tmp4/data4-1.fragment -m 100 -i 1
```
```
DOWNLOAD test/tmp4/download_target4.chunkhash test/tmp4/download_result.fragment
```
run peer 2
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp4/nodes4.map -c test/tmp4/data4-2.fragment -m 100 -i 2
```
run peer 3
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp4/nodes4.map -c test/tmp4/data4-2.fragment -m 100 -i 3
```
