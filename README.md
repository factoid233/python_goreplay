# goreplay

流量回放测试项目
可以解析goreplay录制的文本信息，通过python 请求回放，将录制的响应结果和回放的响应结果进行对比，将差异信息通过csv文件输出

# 流量回放

### 示例

```shell script
python3 python_goreplay.py -c example/my.yaml

```
> -c 配置文件采用yaml格式 可自定义传入配置文件路径
### 指令详解

- host1/host2 回放服务器域名1/域名2
  > 只填 host1 时只回放一台服务器并与回放文件中的响应相比较
  >host1 host2同时传入 回放两台服务器并比较两台服务的响应结果
- speed 回放倍率 1 表示1倍 
- gor_path 回放的文件路径
- no-diff true or false 填写是只请求并记录不比较  默认false
- rules_filter 过滤规则 
    > 1. replace_dict 替换post和get参数中的key对应的value值 
    > 2. delete_uri uri黑名单，回放时删除这些uri的请求 
    > 3. filter_needed_uri uri白名单 此选项填写时，只回放该传入的uri，其他的请求均被舍弃
    > 4. filter_needed_params_or  白名单 过滤get请求参数中含有key的请求，列表内多个值为或者关系
  
