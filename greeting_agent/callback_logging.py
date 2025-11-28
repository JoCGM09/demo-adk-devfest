from google.cloud import logging as google_cloud_logging

logging_client = google_cloud_logging.Client()
logger = logging_client.logger("greeting-agent")

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse

from typing import Optional

def log_consulta_modelo(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    
    agent_name = callback_context.agent_name
    if llm_request.contents and llm_request.contents[-1].role == 'user':
        for part in llm_request.contents[-1].parts:
            if part.text:
                # CORRECCIÓN para INFO
                logger.log(f"[Callback] Consulta al agente {agent_name}: {part.text}", severity="INFO")


def log_respuesta_modelo(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    
    agent_name = callback_context.agent_name

    if llm_response.content and llm_response.content.parts:
        first_part = llm_response.content.parts[0]
        agent_response = getattr(first_part, "text", None)
        function_response = getattr(first_part, "function_call", None)

        if agent_response:
            logger.log(f"[Callback] Respuesta del agente {agent_name}: {agent_response}", severity="INFO")
        elif function_response:
            name = getattr(function_response, "name", str(function_response))
            logger.log(f"[Callback] Llamada a la funcion del agente {agent_name}: {name}", severity="INFO")
        else:
            logger.log(f"[Callback] Respuesta del agente {agent_name} sin contenido reconocible.", severity="INFO")
            return None

    elif getattr(llm_response, "error_message", None):
        logger.log(f"[Callback] Error del agente {agent_name}: {llm_response.error_message}", severity="ERROR")
        return None
    else:
        logger.log(f"[Callback] Respuesta del agente {agent_name} sin contenido.", severity="INFO")
        return None


