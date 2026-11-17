# 惠园智答（Campus AI Assistant）

一个面向对外经济贸易大学在校学生使用场景的校园通知问答**赛事演示原型**。项目中的 8 条通知均为自编模拟数据，**不是学校真实公告**，报名入口也不是真实网址。

## 功能

- 自然语言查询通知、地点、材料、截止时间与来源；多条竞赛可按截止时间排序。
- 每条回答展示本地通知编号、标题与原文；缺少的信息明确提示，不自行补全。
- 通过 `updated_from` 显式关联新旧版本，展示变更；过期报名自动标记。
- 配置 DeepSeek 后生成简短 AI 摘要；事实清单与原文仍由 Python 从本地 JSON 生成。无密钥或 API 失败时自动使用明确标注的本地演示模式。

## 运行

需要 Python 3.10+。在项目目录执行：

```powershell
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开终端显示的地址（通常为 `http://localhost:8501`）。没有 API Key 也能完整体验检索、排序、来源、版本与过期提醒。

启用 DeepSeek：复制 `.env.example` 为 `.env`，将 `DEEPSEEK_API_KEY` 改成自己的密钥。可按需修改 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。`.env` 已加入 `.gitignore`。部署到 Streamlit Community Cloud 时，在应用 Secrets 中配置同名环境变量；不要上传 `.env`。

## 体验问题

1. `数据科学建模赛在哪里举行？`
2. `把所有校园比赛的报名截止时间从早到晚排列`
3. `数据科学建模赛报名材料的原文出处是什么？`
4. `创新创业挑战赛报名费用多少钱？`
5. `创新创业挑战赛最新截止时间是否更新？`
6. `秋季校园文化节还可以报名吗？`

## 测试

```powershell
python -m unittest discover -s tests -v
```

实际执行记录见 `tests/test_results.txt`。API 相关测试使用模拟客户端验证成功、约束拒绝和失败回退；真实 DeepSeek 联网调用需要有效密钥，未在本项目中预置。

## 数据与边界

`notices.json` 中每条均包含来源、版本、原文及演示声明。通知更新仅按明确的 `updated_from` 关系判断。项目不爬取学校网站，不代表学校官方服务，也不能用于真实报名。自然语言检索采用轻量规则，长尾问法可能需要输入活动名称或通知编号。
