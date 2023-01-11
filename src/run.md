Clear socket address usage
```bash
kill -9 $(lsof -i:12345|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48001|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48002|awk '{print $2}'|tail -n 1)
cd ..
python3 util/make_data.py example/ex_file.tar ./example/data1.fragment 4 1
python3 util/make_data.py example/ex_file.tar ./example/data2.fragment 4 2
python3 util/make_data.py example/ex_file.tar ./example/data3.fragment 4 3
python3 util/make_data.py example/ex_file.tar ./example/data4.fragment 4 4
sed -n "1p" master.chunkhash > example/download1.chunkhash
sed -n "2p" master.chunkhash > example/download2.chunkhash
sed -n "3p" master.chunkhash > example/download3.chunkhash
sed -n "4p" master.chunkhash > example/download4.chunkhash
```

Run simulator
```bash
cd ..
perl util/hupsim.pl -m example/ex_topo.map -n example/ex_nodes_map -p 12345 -v 2
```
Run peer1
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p example/ex_nodes_map -c example/data1.fragment -m 1 -i 1 -v 3
```

Run peer2
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p example/ex_nodes_map -c example/data2.fragment -m 1 -i 2 -v 3
```

Run peer3
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p example/ex_nodes_map -c example/data3.fragment -m 1 -i 3 -v 3
```

Run peer4
```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p example/ex_nodes_map -c example/data4.fragment -m 1 -i 4 -v 3
```

This testing script is equivalent to run the following commands in different shells (remember to export SIMULATOR in each shell):

```bash
kill -9 $(lsof -i:12345|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48001|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48002|awk '{print $2}'|tail -n 1)
kill -9 $(lsof -i:48003|awk '{print $2}'|tail -n 1)
cd ..
clear
perl util/hupsim.pl -m test/tmp4/topo4.map -n test/tmp4/nodes4.map -p 12345 -v 3
```

```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp4/nodes4.map -c test/tmp4/data4-1.fragment -m 100 -i 1
```
DOWNLOAD test/tmp4/download_target4.chunkhash test/tmp4/download_result.fragment

```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp4/nodes4.map -c test/tmp4/data4-2.fragment -m 100 -i 2
```
(CTRL+C to terminate peer2 after 1 seconds)

```bash
cd ..
export SIMULATOR="127.0.0.1:12345"
clear
python3 src/peer.py -p test/tmp4/nodes4.map -c test/tmp4/data4-2.fragment -m 100 -i 3
```

