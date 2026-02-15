import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./best_of_opera.db")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
EXPORT_PATH = os.getenv("EXPORT_PATH", "")

HOOK_CATEGORIES = {
    "curiosidade_musica": {
        "label": "Curiosidade Sobre a Música",
        "emoji": "🎵",
        "prompt": "Aborde uma curiosidade fascinante sobre esta música/ária — sua origem, contexto na ópera, significado oculto do texto, ou um fato surpreendente sobre sua composição.",
    },
    "curiosidade_interprete": {
        "label": "Curiosidade Sobre o Intérprete",
        "emoji": "🎤",
        "prompt": "Explore uma curiosidade marcante sobre o intérprete — um momento decisivo na carreira, uma história de bastidor, uma peculiaridade vocal, ou algo que poucos sabem.",
    },
    "curiosidade_compositor": {
        "label": "Curiosidade Sobre o Compositor",
        "emoji": "✍️",
        "prompt": "Revele algo fascinante sobre o compositor — circunstâncias da criação, rivalidades, inspirações pessoais, ou fatos surpreendentes da sua vida.",
    },
    "valor_historico": {
        "label": "Valor Histórico",
        "emoji": "📜",
        "prompt": "Destaque a importância histórica desta performance ou gravação — o que a torna um marco, por que é considerada referência, ou como mudou a história da ópera.",
    },
    "climax_vocal": {
        "label": "Clímax Vocal",
        "emoji": "🔥",
        "prompt": "Foque no momento de clímax vocal — a nota impossível, o agudo arrepiante, a passagem tecnicamente extraordinária que define esta interpretação.",
    },
    "peso_emocional": {
        "label": "Peso Emocional",
        "emoji": "💔",
        "prompt": "Explore a carga emocional profunda — o drama do enredo, a emoção visível do intérprete, ou a conexão entre a história pessoal do artista e o papel.",
    },
    "transformacao_progressiva": {
        "label": "Transformação Progressiva",
        "emoji": "🌅",
        "prompt": "Narre a transformação que acontece durante a performance — como a interpretação evolui, cresce e se transforma do início ao clímax.",
    },
    "dueto_encontro": {
        "label": "Dueto / Encontro",
        "emoji": "🤝",
        "prompt": "Explore a dinâmica do encontro entre vozes — a química entre os intérpretes, o diálogo vocal, a tensão ou harmonia entre as partes.",
    },
    "reacao_impacto_visual": {
        "label": "Reação / Impacto Visual",
        "emoji": "😱",
        "prompt": "Foque no impacto visual e nas reações — a plateia em êxtase, aplausos de pé, lágrimas na audiência, ou o momento que viralizou.",
    },
    "conexao_cultural": {
        "label": "Conexão Cultural",
        "emoji": "🌍",
        "prompt": "Conecte esta performance com cultura popular, cinema, momentos icônicos da TV, ou referências que o público geral reconhece.",
    },
    "prefiro_escrever": {
        "label": "Prefiro Escrever",
        "emoji": "✏️",
        "prompt": "",
    },
}
