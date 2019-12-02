# device-simulator

## 証明書のセットアップ

ダウンロードした証明書`cxxxxxxxxx-certificate.pem.crt`を`certificate.pem`にリネームして`cert`フォルダに格納する。
ダウンロードした鍵`cxxxxxxxxx-private.pem.key`を`private.pem`にリネームして`cert`フォルダに格納する。

## 起動

```bash
python client.py -e "xxxxxxxxxxxxx-xxx.iot.us-west-2.amazonaws.com" -id "device01" -t "sdk/test/Python" -m "both"
```

- -e : IoT Core のエンドポイントを指定する
- -id : 任意の client id を指定する
- -t : トピックを指定する
- -m : モードを指定する（'both', 'publish', 'subscribe'）

python client.py -e "a2no1rce9adht-ats.iot.us-west-2.amazonaws.com" -id "device01" -t "sdk/test/Python" -m "both" --sensor 3
# device-simulator
