"""前台应用默认配置（AppConfig 各 key 默认值；DB 已有值时以 DB 为准）"""

APP_CONFIG_DEFAULTS = {
    'greeting': {'enabled': True,
                 'text': '你好，我是经管之星·AI问数助手，可以就经营台账与统计报表向你提供数据问答服务。',
                 'questions': ['各产品线销售情况', '北京的产品线收入情况', '深圳的产品销售情况']},
    'suggestions': True,
    'tts': False,
    'stt': False,
    'modelConfig': True,
    'hotRecommend': {'enabled': True, 'threshold': 3},
}
