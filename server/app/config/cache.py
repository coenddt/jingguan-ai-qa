"""问法缓存参数：模糊检索相似度权重 / 命中阈值 / 返回条数"""

# 相似度合成权重：bigram Jaccard / 归一化编辑距离
SIM_JACCARD_W = 0.6
SIM_LEV_W = 0.4

# 模糊检索命中阈值
FUZZY_MIN_SCORE = 0.55

# 模糊检索默认返回条数（few-shot 注入上限）
FUZZY_TOP_K = 3
