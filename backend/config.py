import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from utils.data_handler import settings

load_dotenv()

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///data/jobs.sqlite')
}
scheduler = AsyncIOScheduler(jobstores=jobstores)



# COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
GEMINI_API_KEY = settings.get("gemini_api_key") or "AIzaSyBDb_dCejMTVjnuCB9WreDK4Vb23YJykQs"
DEEPGRAM_API_KEY = settings.get("deepgram_api_key") or "2d9259028746938c0d4a7f0279acf753e7018c2f"
# LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
# LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

COMPOSIO_API_KEY="vd1fbu7up23up8x7pluhm"
LANGFUSE_PUBLIC_KEY="pk-lf-e6f7fa20-a3e6-4512-823d-ffc15900fb9a"
LANGFUSE_SECRET_KEY="sk-lf-2744c8d6-0bdd-481e-9bfd-e7da96c54e3d"

os.environ["COMPOSIO_API_KEY"] = COMPOSIO_API_KEY
os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
os.environ["DEEPGRAM_API_KEY"] = DEEPGRAM_API_KEY