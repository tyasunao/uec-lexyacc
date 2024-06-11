# uec-lexyacc

電気通信大学情報理工学域I類（情報系）J5 実験用の Jupyter Notebook です．
LexとYaccの実行用Kernelと，授業資料のファイルが置いてあります．

[Docker hub](https://hub.docker.com/repository/docker/tyasunao/uec-lexyacc/general) からpullして，以下のコマンドでローカルにJupyter Notebookが起動できます．

```bash
% docker run -it --rm -p 8888:8888 uec-lexyacc jupyter notebook --NotebookApp.default_url=/lab/ --ip=0.0.0.0 --port=8888
```

Binderでも実行できます．
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/tyasunao/uec-lexyacc/main)
