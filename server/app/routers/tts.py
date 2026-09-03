from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.errors import BusinessError
from app.services.tt_service import synthesize

router = APIRouter(prefix='/api', tags=['tts'])


class TtsIn(BaseModel):
    text: str


@router.post('/tts')
async def tts(body: TtsIn):
    try:
        audio = await synthesize(body.text)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return Response(content=audio, media_type='audio/mpeg')
