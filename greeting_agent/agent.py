import os
from dotenv import load_dotenv
import google.auth
from pathlib import Path

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from typing import List

from google.adk.tools import ToolContext
from greeting_agent.callback_logging import log_consulta_modelo, log_respuesta_modelo


# Load environment variables from .env file in root directory
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)


# Use default project from credentials if not in .env
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

############################# TOOLS #############################


def guardar_atracciones_al_estado(tool_context: ToolContext, atracciones: List[str]) -> dict[str, str]:
    """
    Almacena la lista de atracciones en state["atracciones"].

    Args:
        atracciones (List[str]): Lista de strings de atracciones turísticas.

    Returns:
        dict[str, str]: Un diccionario con la clave "estado" y un mensaje de confirmación.
    """
    atracciones_existentes = tool_context.state.get("atracciones", [])
    tool_context.state["atracciones"] = atracciones_existentes + atracciones
    return {"estado": "Lista de atracciones actualizada correctamente."}

def guardar_pais_al_estado(tool_context: ToolContext, pais: str) -> dict[str, str]:
    """
    Almacena el país seleccionado en state["pais"].

    Args:
        pais (str): Nombre del país seleccionado por el usuario.

    Returns:
        dict[str, str]: Un diccionario con la clave "estado" y un mensaje de confirmación.
    """
    tool_context.state["pais"] = pais
    return {"estado": f"País seleccionado actualizado: {pais}"}

def guardar_itinerario_al_estado(tool_context: ToolContext, itinerario: List[dict]) -> dict[str, str]:
    """
    Almacena itinerario día-por-día en state["itinerario"].
    Formato esperado: [{"dia": 1, "hora_inicio": "09:00", "actividad": "...", "ubicacion": "..."}, ...]
    """
    tool_context.state["itinerario"] = itinerario
    return {"estado": f"Itinerario guardado: {len(itinerario)} días planificados"}

def guardar_presupuesto_al_estado(tool_context: ToolContext, presupuesto: dict) -> dict[str, str]:
    """
    Almacena presupuesto y opciones de booking en state["presupuesto"].
    Formato: {"total": 2500, "vuelos": 800, "hotel": 1200, "atracciones": 500, "enlaces": [...]}
    """
    tool_context.state["presupuesto"] = presupuesto
    return {"estado": f"Presupuesto calculado: ${presupuesto.get('total', 0)}"}

def guardar_busquedas_al_estado(tool_context: ToolContext, busquedas: dict) -> dict[str, str]:
    """
    Almacena resultados de búsquedas web en state["busquedas"].
    Formato: {"hoteles": [...], "vuelos": [...], "atracciones": [...]}
    """
    tool_context.state["busquedas"] = busquedas
    return {"estado": "Resultados de búsquedas web guardados correctamente."}


#### TODO TOOL PARA EXPORTAR A ARCHIVO #####


############################ Agentes ############################

##### Agente generador de itinerario ######

generador_itinerario = LlmAgent(
    name="generador_itinerario",
    model='gemini-2.5-flash',
    description="Crea un itinerario detallado con fechas, horarios y transporte",
    instruction="""
    Lee state["pais"] y state["atracciones"].
    Pregunta al usuario cuántos días tiene disponibles y sus horarios preferidos.
    Genera un itinerario día-por-día con:
    - Hora de inicio/fin de cada actividad
    - Transporte sugerido entre ubicaciones
    - Tiempo de descanso
    - Recomendaciones de comida
    Luego guarda en state["itinerario"] usando guardar_itinerario_al_estado(itinerario=[...])
    """,
    tools=[guardar_itinerario_al_estado],
)

##### Agente gestor de reservas ######

gestor_reservas = LlmAgent(
    name="gestor_reservas",
    model='gemini-2.5-flash',
    description="Gestiona presupuesto, reservas y confirmaciones",
    instruction="""
    Lee state["itinerario"] y state["atracciones"].
    Calcula:
    - Presupuesto total (vuelos, hotel, atracciones)
    - Opciones de alojamiento en el país
    - Links de booking (Airbnb, Booking, etc.)' y organizalos por precios promedio, solicita al usuario las fechas tentativas de viaje si no las tienes.
    - Seguros de viaje recomendados
    Guarda en state["presupuesto"] usando la tool guardar_presupuesto_al_estado(presupuesto={...}).
    Luego presenta un resumen del presupuesto al usuario y pregunta si desea proceder con las reservas.
    """,
    tools=[guardar_presupuesto_al_estado],

    before_model_callback=log_consulta_modelo,
    after_model_callback=log_respuesta_modelo,  
)

##### TODO Agente exportador de viaje ######


##### Agente planificador de atracciones ######

planificador_atracciones = LlmAgent(
    name="planificador_atracciones",
    model='gemini-2.5-flash',
    description="Un agente que planifica una lista de atracciones turísticas basadas en las preferencias del usuario.",
    instruction="""
    Eres un agente que planifica una lista de atracciones turísticas basadas en las preferencias del usuario.
    Recibe las preferencias del usuario y genera una lista de atracciones turísticas relevantes.
    Debes decirle al usuario que elija qué atracciones realizará para que las puedas almacenar en el estado en la lista de atracciones, no añadas las atracciones directamente al estado sin que el usuario te indique que debes guardarlas.

    Cuando respondas al usuario, **debes usar** la tool 'guardar_atracciones_al_estado' para almacenar las atracciones generadas en el estado cuando el usuario elija las atracciones que realizará.

    **IMPORTANTE**: Al usar la herramienta, pasa tu lista de atracciones como un argumento llamado **'atracciones'**, por ejemplo:
    `guardar_atracciones_al_estado(atracciones=["lista", "de", "atracciones"])`
    
    Antes de planificar, revisa si existe un país seleccionado en `state["pais"]`. Si existe, prioriza y filtra las atracciones basadas en ese país. Si no existe, solicita al usuario que elija un país (o sugiérelo mediante el sub-agente `selector_paises`) antes de proseguir.

    Después de guardar, provee más posibles atracciones al usuario en el chat. 

    Si el usuario solicita ver la lista de atracciones, recupera la lista { atracciones? } mediante bullets del estado y luego sugiere más.
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),

    tools=[guardar_atracciones_al_estado],

    before_model_callback=log_consulta_modelo,
    after_model_callback=log_respuesta_modelo,  
) 

selector_paises = LlmAgent(
    name="selector_paises",
    model='gemini-2.5-flash',
    description="Un agente que ayuda al usuario a elegir países para visitar basados en las preferencias del usuario.",
    instruction="""
    Provee al usuario una lista de países sugeridos para visitar basados en sus preferencias de viaje.
    Ayuda al usuario a identificar su objetivo de viaje: aventura, relajación, cultura, naturaleza, gastronomía, etc.
    Identifica países que coincidan con esos intereses y proporciona información relevante sobre las nacionalidades.
    
    Cuando el usuario selecciona explícitamente un país (por ejemplo: "Quiero ir a España"), usa la tool 'guardar_pais_al_estado' pasando el nombre del país como argumento: `guardar_pais_al_estado(pais="España")`.
    Luego informa al usuario que el país fue guardado y sugiere continuar con la planificación de atracciones (delegando o invocando al sub-agente `planificador_atracciones`).
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),

    tools=[guardar_pais_al_estado],

    before_model_callback=log_consulta_modelo,
    after_model_callback=log_respuesta_modelo,  
)


root_agent = LlmAgent(
    name="greeting_agent",
    model='gemini-2.5-flash',
    description="Asistente de viaje completo: país → atracciones → itinerario → reservas → exportación",
    instruction="""
    Eres un asistente de viajes integral. Guía al usuario a través de estos pasos:
    1. Seleccionar país (selector_paises)
    2. Elegir atracciones (planificador_atracciones)
    3. Crear itinerario detallado (generador_itinerario)
    4. Calcular presupuesto y opciones de reserva (gestor_reservas)
    5. Exportar resumen final (exportador_viaje)
    
    Mantén un tono amigable y ve ofreciendo el siguiente paso cuando el anterior esté completo.
    Siempre pregunta si el usuario quiere continuar antes de pasar al agente siguiente.
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=512,
    ),

    sub_agents=[
        selector_paises,
        planificador_atracciones,
        generador_itinerario,      
        gestor_reservas,                  
    ],

    before_model_callback=log_consulta_modelo,
    after_model_callback=log_respuesta_modelo,
)

