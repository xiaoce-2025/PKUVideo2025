# PKUVideo2025
本程序可以辅助用户进行教学网回放的下载，防止教学网在考试季产生崩溃而无法观看回放。
## 安装方法

1. 安装Python 3.8及以上版本。
2. 安装依赖库：

```bash
pip install -r requirements.txt
```

3. 自行按照chrome安装说明下载并安装相应版本的chrome

## 使用说明

1. 运行 `main.py` 启动图形界面：

```bash
python main.py
```

2. 按界面提示填写IAAA账号、密码、Chrome浏览器路径、保存路径等信息。
3. 点击"获取课程列表"获取可下载的课程。
4. 勾选需要下载的课程，设置最大回放数（-1为全部），点击"开始获取回放下载链接"。
5. 下载结果会自动保存到指定目录。

> 注意：
> - 本工具仅供学习交流使用，使用或研究时请严格遵守[北大树洞管理规范](https://treehole.pku.edu.cn/management_specifications.html)、[北大树洞服务协议](https://treehole.pku.edu.cn/PKU_Hole_User_Agreement.html)、[北京大学网站管理办法](https://ocac.pku.edu.cn/docs/20240605114214122562.pdf)、[中华人民共和国网络安全法](http://www.npc.gov.cn/zgrdw/npc/xinwen/2016-11/07/content_2001605.htm)等等一系列相关法律法规和校级规章。对于由于使用者不遵守相关规定而造成的一切后果，本程序不承担任何责任。对于开发者在此项目上的延伸导致的一切问题，本程序不承担任何责任。
> - 请勿在公开场合传播此项目（如树洞）
