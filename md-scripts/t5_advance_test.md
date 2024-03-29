```bash
kill -9 $(lsof -i:12345|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48001|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48002|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48003|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48004|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48005|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48006|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48007|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48008|awk '{print $2}'|tail -n 1)
cd ..
clear
mkdir test/tmp5/results
perl util/hupsim.pl -m test/tmp5/topo5.map -n test/tmp5/nodes5.map -p 12345 -v 3
```

Run peer1
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-1.fragment -m 100 -i 1
```
```
DOWNLOAD test/tmp5/targets/target1.chunkhash test/tmp5/results/result1.fragment
```
Run peer2
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-2.fragment -m 100 -i 2
```
Run peer3
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-3.fragment -m 100 -i 7
```
```
DOWNLOAD test/tmp5/targets/target2.chunkhash test/tmp5/results/result2.fragment
```
Run peer4
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-4.fragment -m 100 -i 14
```
Run peer5
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-5.fragment -m 100 -i 10
```
```
DOWNLOAD test/tmp5/targets/target3.chunkhash test/tmp5/results/result3.fragment
```
Run peer6
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-6.fragment -m 100 -i 15
```
Run peer7
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-7.fragment -m 100 -i 12
```
Run peer8
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp5/nodes5.map -c test/tmp5/fragments/data5-8.fragment -m 100 -i 13
```
```
DOWNLOAD test/tmp5/targets/target4.chunkhash test/tmp5/results/result4.fragment
```