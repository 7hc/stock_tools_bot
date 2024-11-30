## 一个股票盈亏查询小工具

目前仅支持企业微信应用

**详细的配置说明可见 [使用轻量服务器+企业微信搭建股票盈亏查询Bot](https://www.9kr.cc/archives/597/)**

### 使用方法

> 使用Dockerfile构建镜像

```
docker build -t stock_tools_bot:0.1 .
```

> 创建容器 

```
docker run -d -p 80:8000 -v ./conf.json:/workspace/conf.json -v ./data.json:/workspace/data.json stock_tools_bot:0.1
```

> 配置企业微信应用

略，详见上面的详细配置说明

> 修改配置文件`conf.json`(用来放企业微信应用相关配置)

```
{
    "CorpID":"企业ID",
    "AgentId":"应用ID，可以在应用主页找到",
    "Secret":"应用Secret，可以在应用主页找到",
    "Token":"回调Token，可以在设置回调处找到",
    "EncodingAESKey":"回调加解密密钥，可在设置回调处找到"
}
```

> 修改配置文件`data.json`(用来放股票持仓信息)

- key为股票代码，value为股票信息
- n为股票名称，v为持仓数量，p为成本价格

```
{
    "SZ002299":{"n":"圣农发展","v":3000,"p":"19.82"},
    "SH601231":{"n":"环旭电子","v":7000,"p":"13.31"}
}
```
