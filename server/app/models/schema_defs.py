"""15 个核心模型的 mongo-store JSON schema（§4.3 契约，唯一事实源）"""

_BIZ_RW = {'read': ['internal', 'query'], 'write': ['internal']}
_SYS_RW = {'read': ['internal'], 'write': ['internal']}

COMMERCIAL_LEDGER_SCHEMA = {
    'name': 'CommercialLedger', 'collection': 'commercial_ledger',
    'idPrefix': 'CL', 'timestamps': True,
    'fields': {
        'signDate': {'type': 'string', 'default': ''},
        'year': 'int', 'quarter': 'int', 'month': 'int',
        'unit': {'type': 'string', 'default': ''},
        'industry': {'type': 'string', 'default': ''},
        'productLine': {'type': 'string', 'default': ''},
        'productModel': {'type': 'string', 'default': ''},
        'contractAmt': {'type': 'float', 'default': 0.0},
        'income': {'type': 'float', 'default': 0.0},
        'customer': {'type': 'string', 'default': ''},
    },
    'indexes': [
        {'keys': {'year': 1, 'unit': 1}},
        {'keys': {'year': 1, 'industry': 1}},
        {'keys': {'year': 1, 'productLine': 1}},
        {'keys': {'year': 1, 'month': 1}},
    ],
    **_BIZ_RW,
}

PPL_LEDGER_SCHEMA = {
    'name': 'PplLedger', 'collection': 'ppl_ledger',
    'idPrefix': 'PPL', 'timestamps': True,
    'fields': {
        'year': 'int',
        'projectName': {'type': 'string', 'default': ''},
        'unit': {'type': 'string', 'default': ''},
        'industry': {'type': 'string', 'default': ''},
        'contractAmt': {'type': 'float', 'default': 0.0},
        'stage': {'type': 'string', 'default': ''},
        'riskLevel': {'type': 'string', 'default': '中'},
    },
    'indexes': [{'keys': {'year': 1, 'riskLevel': 1}}],
    **_BIZ_RW,
}

GOAL_LEDGER_SCHEMA = {
    'name': 'GoalLedger', 'collection': 'goal_ledger',
    'idPrefix': 'GL', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'commercialGoal': {'type': 'float', 'default': 0.0},
        'solutionGoal': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}

REPORT_OVERALL_SCHEMA = {
    'name': 'ReportOverall', 'collection': 'report_overall',
    'idPrefix': 'RO', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'income': {'type': 'float', 'default': 0.0},
        'gcIncome': {'type': 'float', 'default': 0.0},
        'znIncome': {'type': 'float', 'default': 0.0},
        'bsIncome': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}

REPORT_PRODUCT_SCHEMA = {
    'name': 'ReportProduct', 'collection': 'report_product',
    'idPrefix': 'RP', 'timestamps': True,
    'fields': {
        'year': 'int',
        'productLine': {'type': 'string', 'default': ''},
        'income': {'type': 'float', 'default': 0.0},
        'yoy': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'productLine': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}

REPORT_SOLUTION_SCHEMA = {
    'name': 'ReportSolution', 'collection': 'report_solution',
    'idPrefix': 'RS2', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'solutionIncome': {'type': 'float', 'default': 0.0},
        'solutionGoal': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}

REPORT_INDUSTRY_SCHEMA = {
    'name': 'ReportIndustry', 'collection': 'report_industry',
    'idPrefix': 'RI', 'timestamps': True,
    'fields': {
        'year': 'int',
        'industry': {'type': 'string', 'default': ''},
        'income': {'type': 'float', 'default': 0.0},
        'gcIncome': {'type': 'float', 'default': 0.0},
        'znIncome': {'type': 'float', 'default': 0.0},
        'bsIncome': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'industry': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}

REPORT_KEY_UNIT_SCHEMA = {
    'name': 'ReportKeyUnit', 'collection': 'report_key_unit',
    'idPrefix': 'RKU', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'orderAmt': {'type': 'float', 'default': 0.0},
        'notRecvAmt': {'type': 'float', 'default': 0.0},
        'riskCount': {'type': 'int', 'default': 0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}

QA_SESSION_SCHEMA = {
    'name': 'QaSession', 'collection': 'qa_session',
    'idPrefix': 'QS', 'timestamps': True,
    'fields': {
        'title': {'type': 'string', 'default': ''},
        'pinned': {'type': 'boolean', 'default': False},
        'userName': {'type': 'string', 'default': '管理员'},
        'msgCount': {'type': 'int', 'default': 0},
    },
    'indexes': [{'keys': {'pinned': -1, 'updatedAt': -1}}],
    **_SYS_RW,
}

QA_MESSAGE_SCHEMA = {
    'name': 'QaMessage', 'collection': 'qa_message',
    'idPrefix': 'QM', 'timestamps': True,
    'fields': {
        'sessionId': {'type': 'string', 'default': ''},
        'role': {'type': 'string', 'default': 'user'},
        'content': {'type': 'string', 'default': ''},
        'aiMeta': {'type': 'object', 'default': {}},
    },
    'indexes': [{'keys': {'sessionId': 1}}, {'keys': {'createdAt': -1}}],
    **_SYS_RW,
}

APP_CONFIG_SCHEMA = {
    'name': 'AppConfig', 'collection': 'app_config',
    'idPrefix': 'CFG', 'timestamps': True,
    'fields': {'key': {'type': 'string', 'default': ''}, 'value': {'type': 'any'}},
    'indexes': [{'keys': {'key': 1}, 'options': {'unique': True}}],
    **_SYS_RW,
}

AI_MODEL_SCHEMA = {
    'name': 'AiModel', 'collection': 'ai_model',
    'idPrefix': 'M', 'timestamps': True,
    'fields': {
        'name': {'type': 'string', 'default': ''},
        'baseUrl': {'type': 'string', 'default': ''},
        'apiKey': {'type': 'string', 'default': ''},
        'modelName': {'type': 'string', 'default': ''},
        'enabled': {'type': 'boolean', 'default': False},
    },
    **_SYS_RW,
}

FEEDBACK_SCHEMA = {
    'name': 'Feedback', 'collection': 'feedback',
    'idPrefix': 'FB', 'timestamps': True,
    'fields': {
        'sessionId': {'type': 'string', 'default': ''},
        'question': {'type': 'string', 'default': ''},
        'answer': {'type': 'string', 'default': ''},
        'userName': {'type': 'string', 'default': '管理员'},
        'description': {'type': 'string', 'default': ''},
        'status': {'type': 'string', 'default': '待处理'},
        'remark': {'type': 'string', 'default': ''},
    },
    'indexes': [{'keys': {'status': 1, 'createdAt': -1}}],
    **_SYS_RW,
}

IMPORT_LOG_SCHEMA = {
    'name': 'ImportLog', 'collection': 'import_log',
    'idPrefix': 'IL', 'timestamps': True,
    'fields': {
        'type': {'type': 'string', 'default': ''},
        'year': {'type': 'int', 'default': 0},
        'fileName': {'type': 'string', 'default': ''},
        'totalRows': {'type': 'int', 'default': 0},
        'successRows': {'type': 'int', 'default': 0},
        'status': {'type': 'string', 'default': ''},
        'detail': {'type': 'string', 'default': ''},
        'userName': {'type': 'string', 'default': '管理员'},
    },
    'indexes': [{'keys': {'createdAt': -1}}],
    **_SYS_RW,
}

QUERY_EXAMPLE_SCHEMA = {
    'name': 'QueryExample', 'collection': 'query_example',
    'idPrefix': 'QE', 'timestamps': True,
    'fields': {
        'question': {'type': 'string', 'default': ''},
        'qnorm': {'type': 'string', 'default': ''},
        'template': {'type': 'object', 'default': {}},
        'favor': {'type': 'int', 'default': 1},
        'hit': {'type': 'int', 'default': 0},
        'schemaVer': {'type': 'string', 'default': ''},
    },
    'indexes': [{'keys': {'qnorm': 1}, 'options': {'unique': True}}, {'keys': {'hit': -1}}],
    **_SYS_RW,
}

ALL_SCHEMAS = [
    COMMERCIAL_LEDGER_SCHEMA, PPL_LEDGER_SCHEMA, GOAL_LEDGER_SCHEMA,
    REPORT_OVERALL_SCHEMA, REPORT_PRODUCT_SCHEMA, REPORT_SOLUTION_SCHEMA,
    REPORT_INDUSTRY_SCHEMA, REPORT_KEY_UNIT_SCHEMA,
    QA_SESSION_SCHEMA, QA_MESSAGE_SCHEMA, APP_CONFIG_SCHEMA,
    AI_MODEL_SCHEMA, FEEDBACK_SCHEMA, IMPORT_LOG_SCHEMA, QUERY_EXAMPLE_SCHEMA,
]
