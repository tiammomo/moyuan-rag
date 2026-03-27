# 06 璋冭瘯涓庨獙璇?
## 涓轰粈涔?RAG 椤圭洰涓€瀹氳鏈夎仈璋冮獙璇?
鍥犱负瀹冧笉鏄崟浣撳簲鐢紝鑰屾槸涓€鏁村澶氱粍浠剁郴缁燂細

- 鍓嶇
- 鍚庣
- worker
- MySQL
- Redis
- Kafka
- Elasticsearch
- Milvus

濡傛灉鍙湅鍗曚釜鎺ュ彛鏄惁杩斿洖 `200`锛屽苟涓嶈兘璇佹槑鏁存潯閾捐矾鍙敤銆?
## 鏈€鍏堢湅浠€涔?
鍏堢湅鏈嶅姟鏄惁鍋ュ悍锛?
```bash
python backend/scripts/rag_stack.py status
```

杩樺彲浠ョ洿鎺ョ湅锛?
- 鍓嶇锛歚http://localhost:33004`
- 鍚庣鍋ュ悍妫€鏌ワ細`http://localhost:38084/health`
- Swagger锛歚http://localhost:38084/docs`

## 濡備綍楠岃瘉瀹屾暣鍏ュ簱閾捐矾

鎺ㄨ崘鐩存帴璺戞湰鍦伴泦鎴愯剼鏈細

```bash
python backend/scripts/local_integration.py --start-infra
```

瀹冧細楠岃瘉锛?
- 鍩虹鏈嶅姟鏄惁鍙敤
- 杩佺Щ鏄惁鎵ц
- 涓婁紶鍒板悜閲忓寲鏄惁璺戦€?- MySQL銆丒lasticsearch銆丮ilvus 鏄惁涓€鑷磋惤搴?
## 涓婁紶鍗′綇鏃跺厛鐪嬪摢閲?
### 鍋滃湪 `uploading`

浼樺厛鎺掓煡锛?
- backend 鏄惁鎴愬姛鍙戝嚭 Kafka 娑堟伅
- Kafka / worker 鏄惁姝ｅ父杩愯

### 鍋滃湪 `parsing`

浼樺厛鎺掓煡锛?
- parser worker 鏃ュ織
- 鏂囦欢瑙ｆ瀽鏄惁澶辫触
- 鍘熸枃浠惰矾寰勬槸鍚﹀彲璇?
### 鍋滃湪 `splitting`

浼樺厛鎺掓煡锛?
- splitter worker 鏃ュ織
- parser artifact 鏄惁瀛樺湪

### 鍋滃湪 `embedding`

浼樺厛鎺掓煡锛?
- vectorizer worker 鏃ュ織
- embedding 妯″瀷鏄惁鍙敤
- Elasticsearch / Milvus 鏄惁姝ｅ父鍐欏叆

## 鐪嬫棩蹇楁€庝箞鍋?
```bash
python backend/scripts/rag_stack.py logs --services backend parser splitter vectorizer --tail 50
```

## 閲嶅惎鍗曚釜鏈嶅姟鎬庝箞鍋?
```bash
python backend/scripts/rag_stack.py restart backend
```

## Kafka 鐩稿叧闂鎬庝箞澶勭悊

杩欎釜椤圭洰宸茬粡鍋氫簡锛?
- 鎵嬪姩鎻愪氦 offset
- DLQ
- replay 宸ュ叿

鎵€浠ュ綋娑堟伅澶辫触鏃讹紝涓嶆槸绠€鍗曚涪鎺夛紝鑰屾槸鍙互缁х画杩借釜鍜屽洖鏀俱€?
## 濡備綍鐞嗚В鈥滄祴璇曢€氳繃鈥?
瀵硅繖涓」鐩潵璇达紝鐪熸鐨勨€滈€氳繃鈥濊嚦灏戞剰鍛崇潃锛?
- 鍓嶅悗绔彲璁块棶
- 鏂囨。鑳藉畬鎴愬叆搴?- ES 鏈?chunk
- Milvus 鏈夊悜閲?- 鏂囨。鐘舵€佽兘杩涘叆 `completed`

## 鏈€鍚庤浣忎竴鍙ヨ瘽

RAG 椤圭洰鐨勯獙璇佷笉鏄湅鏌愪釜鍑芥暟璺戞病璺戯紝鑰屾槸鐪嬧€滀粠涓婁紶鍒扮瓟妗堚€濈殑鏁存潯閾捐矾鏈夋病鏈夐棴鐜€?
