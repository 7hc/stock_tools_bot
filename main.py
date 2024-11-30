import requests,json,time,uvicorn,base64,hashlib,xmltodict
from fastapi import BackgroundTasks, FastAPI, Request, Response
from Crypto.Cipher import AES

class xmlTools:
    def xml2json(xmldat):
        if type(xmldat) == bytes:
            xmlstr = str(xmldat,encoding='utf-8')
        else:
            xmlstr = xmldat
        # print(xmlstr)
        #parse是的xml解析器
        xmlparse = xmltodict.parse(xmlstr)
        #json库dumps()是将dict转化成json格式，loads()是将json转化成dict格式。
        #dumps()方法的ident=1，格式化json
        jsonstr = (json.dumps(xmlparse,indent=1))
        jsondat = json.loads(jsonstr)
        return jsondat

# 检查base64编码后数据位数是否正确
def check_base64_len(base64_str):
    len_remainder = 4 - (len(base64_str) % 4)
    if len_remainder == 0:
        return base64_str
    else:
        for temp in range(0,len_remainder):
            base64_str = base64_str + "="
        return base64_str
# 解密并提取消息正文
def msg_base64_decrypt(ciphertext_base64,key_base64):
    # 处理密文、密钥和iv
    ciphertext_bytes = base64.b64decode(check_base64_len(ciphertext_base64))
    key_bytes = base64.b64decode(check_base64_len(key_base64))
    iv_bytes = key_bytes[:16]

    # 解密
    decr = AES.new(key_bytes,AES.MODE_CBC,iv_bytes)
    plaintext_bytes = decr.decrypt(ciphertext_bytes)

    # 截取数据，判断消息正文字节数
    msg_len_bytes = plaintext_bytes[16:20]
    msg_len = int.from_bytes(msg_len_bytes,byteorder='big', signed=False)

    # 根据消息正文字节数截取消息正文，并转为字符串格式
    msg_bytes = plaintext_bytes[20:20+msg_len]
    msg = str(msg_bytes,encoding='utf-8')

    return msg

# 消息体签名校验
def check_msg_signature(msg_signature,token,timestamp,nonce,echostr):
    # 使用sort()从小到大排序[].sort()是在原地址改值的，所以如果使用li_s = li.sort()，li_s是空的，li的值变为排序后的值]
    li = [token,timestamp,nonce,echostr]
    li.sort()
    # 将排序结果拼接
    li_str = li[0]+li[1]+li[2]+li[3]

    # 计算SHA-1值
    sha1 = hashlib.sha1()
    # update()要指定加密字符串字符代码，不然要报错：
    # "Unicode-objects must be encoded before hashing"
    sha1.update(li_str.encode("utf8"))
    sha1_result = sha1.hexdigest()

    # 比较并返回比较结果
    if sha1_result == msg_signature:
        return True
    else:
        return False

def new_query(UserName):
    with open("data.json", "r",encoding="utf8") as f:
        data = json.loads(f.read())
    cq = check_quotec(data.keys())
    print(cq)
    btext = "---当前盈亏---\n"
    all = 0.0
    for c in cq:
        btext = btext + data[c]["n"] + ": " + str(round((float(data[c]["v"]) * (float(cq[c]) - float(data[c]["p"]))),2)) + "\n"
        all += round((float(data[c]["v"]) * (float(cq[c]) - float(data[c]["p"]))),2)
    btext = btext + "合计: " + str(round(all,2))
    print(btext)
    send_wx_msg(btext,get_acctoken(get_config("CorpID"),get_config("Secret")),UserName,get_config("AgentId"))

def get_acctoken(ID,SECRET):
    url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={ID}&corpsecret={SECRET}'
    r = requests.get(url)
    acctoken = r.json()["access_token"]
    return acctoken

def get_config(key):
    with open("conf.json", "r",encoding="utf8") as f:
        data = json.loads(f.read())
        if key in data.keys():
            return data[key]
        else:
            return None

def send_wx_msg(msg,acctoken,UserName,AgentID):
    url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={acctoken}'
    postdat = {
                "touser": UserName,
                "msgtype": "text",
                "agentid": int(AgentID),
                "text": {
                    "content": str(msg).encode().decode('utf-8')
                }
            }
    r = requests.post(url=url,json=postdat)
    try:
        print(r.text)
    except Exception as e:
        print(e)

app = FastAPI()

# 查询价格
def check_quotec(data:list):
    quotec = ""
    for n in data:
        quotec += n + ","
    quotec = quotec[:-1]
    
    url = "https://stock.xueqiu.com/v5/stock/realtime/quotec.json?symbol={}&_={}".format(quotec,time.time()*1000)
    headers = {
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    }
    r = requests.get(url,headers=headers)
    if r.status_code == 200:
        rj = r.json()
        dat = {}
        for q in rj["data"]:
            dat[q["symbol"]] = q["current"]
        return dat
    return False

# 接收企业微信应用信息
@app.post("/api/v1/workwx_app")
async def workwx_app(request: Request,backgroundTasks:BackgroundTasks):

    body = await request.body()
    json_data = xmlTools.xml2json(body)
    Encrypt = json_data["xml"]["Encrypt"]
    plainTextRes = msg_base64_decrypt(Encrypt,get_config("EncodingAESKey"))
    plainTextDataJson = xmlTools.xml2json(plainTextRes)
    MsgType = plainTextDataJson['xml']['MsgType']
    ToUserName = json_data["xml"]["ToUserName"]
    if MsgType == "text":
        Content = plainTextDataJson['xml']['Content']
        FromUserName = plainTextDataJson["xml"]["FromUserName"]
        if Content == "now":
            backgroundTasks.add_task(new_query,FromUserName)
            return Response(content="", media_type="text/xml")
    else:
        return Response(content="", media_type="text/xml")

# URL验证
@app.get("/api/v1/workwx_app")
def workwx_app_check(msg_signature:str,timestamp:str,nonce:str,echostr:str):
    
    if not check_msg_signature(msg_signature,get_config("Token"),timestamp,nonce,echostr):
        return Response(content="error",status_code=400)
    else:
        decrypt_result = msg_base64_decrypt(echostr,get_config("EncodingAESKey"))
        return Response(content=decrypt_result,status_code=200)


if __name__ == "__main__":
    uvicorn.run(app,host="0.0.0.0",port=8000)