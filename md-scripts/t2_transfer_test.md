clear ports
```bash
kill -9 $(lsof -i:12345|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48001|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48002|awk '{print $2}'|tail -n 1)
clear
```
run peer 1
```bash
cd ..
clear
python3 src/peer.py -p test/tmp2/nodes2.map -c test/tmp2/data1.fragment -m 1 -i 1 -t 60
```
```
DOWNLOAD test/tmp2/download_target.chunkhash test/tmp2/download_result.fragment
```
run peer 2
```bash
cd ..
clear
python3 src/peer.py -p test/tmp2/nodes2.map -c test/tmp2/data2.fragment -m 1 -i 2 -t 60
```