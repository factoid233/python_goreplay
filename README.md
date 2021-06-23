# goreplay

流量回放测试项目

# 流量回放

### 示例

```shell script
python3 python_goreplay.py \
-h1 172.16.2.22:8088 \
-h2 172.16.2.211:8182 \
-v 1 \
-p data/test.gor \
-r '{"replace_dict":{"user":"test","client_user":"test","client_channel":"test"},"delete_uri":["/actuator/prometheus"],"filter_needed_uri":
                  ["/api/preloan/add"],"filter_needed_params_or": ["oper"]}'
```

### 指令详解

- -h1/-h2 回放服务器域名1/域名2
  > 只填-h1 时只回放一台服务器并与回放文件中的响应相比较
  >-h1 -h2同时传入 回放两台服务器并比较两台服务的响应结果
- -v 回放倍率 1 表示1倍
- -p 回放的文件路径
- -r 规则 
    > 1. replace_dict 替换post和get参数中的key对应的value值 
    > 2. delete_uri uri黑名单，回放时删除这些uri的请求 
    > 3. filter_needed_uri uri白名单 此选项填写时，只回放该传入的uri，其他的请求均被舍弃
    > 4. filter_needed_params_or  过滤get请求参数中含有key的请求，列表内多个值为或者关系
  