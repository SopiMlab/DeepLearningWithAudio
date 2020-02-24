
from .. import communication_struct as __gss

from generator import handlers as gen_handlers
from hallucination import handlers as hallucination_handlers

handlers = {}
handlers.update(gen_handlers)
handlers.update(hallucination_handlers)