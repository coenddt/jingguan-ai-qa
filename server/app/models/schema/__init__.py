"""16 个核心模型的 mongo-store JSON schema（§4.3 契约，唯一事实源），每 schema 一个文件"""

from app.models.schema.ai_model import AI_MODEL_SCHEMA
from app.models.schema.app_config import APP_CONFIG_SCHEMA
from app.models.schema.auto_feedback import AUTO_FEEDBACK_SCHEMA
from app.models.schema.commercial_ledger import COMMERCIAL_LEDGER_SCHEMA
from app.models.schema.feedback import FEEDBACK_SCHEMA
from app.models.schema.goal_ledger import GOAL_LEDGER_SCHEMA
from app.models.schema.import_log import IMPORT_LOG_SCHEMA
from app.models.schema.ppl_ledger import PPL_LEDGER_SCHEMA
from app.models.schema.qa_message import QA_MESSAGE_SCHEMA
from app.models.schema.qa_session import QA_SESSION_SCHEMA
from app.models.schema.query_example import QUERY_EXAMPLE_SCHEMA
from app.models.schema.report_industry import REPORT_INDUSTRY_SCHEMA
from app.models.schema.report_key_unit import REPORT_KEY_UNIT_SCHEMA
from app.models.schema.report_overall import REPORT_OVERALL_SCHEMA
from app.models.schema.report_product import REPORT_PRODUCT_SCHEMA
from app.models.schema.report_solution import REPORT_SOLUTION_SCHEMA

ALL_SCHEMAS = [
    COMMERCIAL_LEDGER_SCHEMA, PPL_LEDGER_SCHEMA, GOAL_LEDGER_SCHEMA,
    REPORT_OVERALL_SCHEMA, REPORT_PRODUCT_SCHEMA, REPORT_SOLUTION_SCHEMA,
    REPORT_INDUSTRY_SCHEMA, REPORT_KEY_UNIT_SCHEMA,
    QA_SESSION_SCHEMA, QA_MESSAGE_SCHEMA, APP_CONFIG_SCHEMA,
    AI_MODEL_SCHEMA, FEEDBACK_SCHEMA, IMPORT_LOG_SCHEMA, QUERY_EXAMPLE_SCHEMA,
    AUTO_FEEDBACK_SCHEMA,
]
