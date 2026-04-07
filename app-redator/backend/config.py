import os
import json
import time
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./best_of_opera.db")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
EXPORT_PATH = os.getenv("EXPORT_PATH", "")

def _resolve_editor_url() -> str:
    """Resolve EDITOR_API_URL: env var > Railway auto-detect > localhost."""
    url = os.getenv("EDITOR_API_URL")
    if url:
        return url.rstrip("/")
    # Railway: se rodando em container Railway, usar URL pública do editor
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        return "https://editor-backend-production.up.railway.app"
    return "http://localhost:8000"


EDITOR_API_URL = _resolve_editor_url()
BRAND_SLUG = os.getenv("BRAND_SLUG")  # sem default — None se não configurado

_brand_config_cache: dict = {}
_CACHE_TTL = 300


def load_brand_config(slug: str) -> dict:
    """Carrega config da marca do editor via API interna. Cache 5min."""
    if not slug:
        raise ValueError("slug da marca é obrigatório para carregar configuração")
    target_slug = slug
    now = time.monotonic()

    cached = _brand_config_cache.get(target_slug)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    try:
        import urllib.request
        url = f"{EDITOR_API_URL}/api/internal/perfil/{target_slug}/redator-config"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        if not data.get("identity_prompt_redator") and not data.get("tom_de_voz_redator"):
            print(
                f"⚠️ [brand_config] Perfil '{target_slug}' sem identity_prompt_redator "
                f"nem tom_de_voz_redator. Geração usará defaults sem personalidade de marca."
            )
        _brand_config_cache[target_slug] = {"data": data, "ts": now}
        return data
    except Exception as exc:
        print(f"⚠️ load_brand_config: editor offline para slug='{target_slug}' ({exc})")
        raise HTTPException(
            503,
            f"Não foi possível carregar configuração da marca '{target_slug}'. "
            "Editor indisponível. Tente novamente em instantes."
        )


HOOK_CATEGORIES = {
    "curiosidade_musica": {
        "label": "Curiosidade Sobre a Música",
        "emoji": "🎵",
        "prompt": """Foque em um fato surpreendente sobre ESTA música especificamente —
sua origem, como foi composta, algo inesperado sobre a letra ou melodia,
por que ela existe, o que ela representou na época.
NÃO fale do compositor em geral. Fale desta peça.
Estrutura: [o que todos assumem sobre esta música] → [a verdade que surpreende]
Tom: Como revelar um segredo guardado por séculos.
Exemplos de primeiras legendas BOAS:
'Bizet compôs esta ária em menos de uma hora — de ressaca'
'A melodia mais famosa da ópera foi quase cortada no ensaio'
'Esta letra foi escrita por um homem que nunca viveu o que descreve'
PROIBIDO: frases genéricas sobre 'uma das mais famosas' ou 'beleza intemporal'""",
    },
    "curiosidade_interprete": {
        "label": "Curiosidade Sobre o Intérprete",
        "emoji": "🎤",
        "prompt": """Foque em algo surpreendente sobre ESTE intérprete específico —
um fato da vida, uma decisão radical, uma contradição, uma história de
superação ou queda. Não o elogie genericamente: revele algo.
Estrutura: [quem o público acha que é esta pessoa] → [quem ela realmente é]
Tom: Perfil de bastidores, como um jornalista que teve acesso exclusivo.
Exemplos de primeiras legendas BOAS:
'Ela foi rejeitada no conservatório três vezes seguidas'
'Ele cantou isto no dia em que seu pai morreu — sem cancelar'
'A crítica a destruiu na estreia. Ela voltou e fez o mesmo papel 200 vezes'
PROIBIDO: 'voz incrível', 'talento extraordinário', qualquer elogio vago""",
    },
    "curiosidade_compositor": {
        "label": "Curiosidade Sobre o Compositor",
        "emoji": "✍️",
        "prompt": """Foque em um fato específico e surpreendente sobre o compositor —
não uma biografia, mas UM momento, UM conflito, UMA decisão que reveals
quem ele realmente era. Escândalo, obsessão, fracasso, traição, ironia do destino.
Estrutura: [imagem pública que as pessoas têm] → [contradição ou revelação]
Tom: Como descobrir que um ídolo tinha um lado que ninguém contava.
Exemplos de primeiras legendas BOAS:
'Verdi odiava esta ópera que o tornou imortal'
'Mozart morreu sem saber que esta era sua obra-prima'
'Ele roubou a melodia — e foi pago por isso durante 20 anos'
PROIBIDO: datas de nascimento, nacionalidade, 'um dos maiores compositores'""",
    },
    "valor_historico": {
        "label": "Valor Histórico",
        "emoji": "📜",
        "prompt": """Foque no IMPACTO REAL desta música no mundo — não 'é histórica',
mas O QUE mudou por causa dela. Uma guerra que parou. Uma revolução que começou.
Uma lei que mudou. Um preconceito que rachou. Algo concreto que aconteceu.
Estrutura: [o mundo antes] → [o momento desta música] → [o mundo depois]
Tom: Documentário de história que revela que a música mudou fatos reais.
Exemplos de primeiras legendas BOAS:
'Esta ária foi tocada quando o Muro de Berlim caiu'
'Verdi usou esta ópera pra esconder um grito de independência'
'O governo proibiu esta música — ela ficou ainda mais famosa'
PROIBIDO: 'faz parte da história', 'patrimônio cultural', qualquer abstração""",
    },
    "climax_vocal": {
        "label": "Clímax Vocal",
        "emoji": "🔥",
        "prompt": """Foque no momento técnico e humano MAIS EXTREMO desta performance —
a nota impossível, o trecho que separa os que conseguem dos que desistem,
o instante em que o corpo humano faz algo que parece não dever ser possível.
Estrutura: [construção da tensão] → [o que está prestes a acontecer] → [o momento]
Tom: Narração esportiva de alto risco. Como descrever um atleta no limite.
Exemplos de primeiras legendas BOAS:
'O que está prestes a acontecer vai dar arrepio na sua nuca'
'Poucos tenores no mundo conseguem cantar isso ao vivo'
'Ela vai sustentar esta nota por 15 segundos — sem respirar'
PROIBIDO: 'voz poderosa', 'técnica impressionante', qualquer elogio sem especificidade""",
    },
    "peso_emocional": {
        "label": "Peso Emocional",
        "emoji": "💔",
        "prompt": """Foque na emoção humana ESPECÍFICA desta música — não 'é emocionante',
mas QUAL emoção, em QUAL situação da vida humana ela aparece, e POR QUE
esta música captura isso melhor que qualquer outra coisa.
Estrutura: [situação da vida que o ouvinte reconhece] → [como a música existe nesse lugar]
Tom: Confissão íntima. Como escrever para alguém que está passando por aquilo agora.
Exemplos de primeiras legendas BOAS:
'Para quem já perdeu alguém e não conseguiu chorar'
'Esta é a música que toca quando não há mais palavras'
'Ele compôs isto após perder o filho — e você vai sentir cada nota'
PROIBIDO: 'emocionante', 'tocante', 'bela', qualquer adjetivo genérico de emoção""",
    },
    "transformacao_progressiva": {
        "label": "Transformação Progressiva",
        "emoji": "🌅",
        "prompt": """Foque na JORNADA dentro desta música — como ela começa num lugar
e termina em outro completamente diferente. A transformação do personagem,
da harmonia, da intensidade. O arco que faz o ouvinte chegar ao final diferente.
Estrutura: [onde começa] → [o que muda no caminho] → [onde chega — e por que isso importa]
Tom: Como descrever uma viagem sem revelar o destino até o fim.
Exemplos de primeiras legendas BOAS:
'Ela começa pedindo permissão — e termina dando uma ordem'
'Os primeiros 30 segundos parecem paz. Aguarde.'
'A melodia muda uma única nota — e tudo desmorona'
PROIBIDO: 'começa suave e termina forte', qualquer descrição óbvia de dinâmica""",
    },
    "dueto_encontro": {
        "label": "Dueto / Encontro",
        "emoji": "🤝",
        "prompt": """Foque na RELAÇÃO entre as duas vozes — não que 'cantam juntos',
mas O QUE está acontecendo entre eles naquele momento. Conflito, desejo,
despedida, mentira, reconciliação. As vozes como personagens com intenções opostas.
Estrutura: [o que cada voz quer] → [onde elas se encontram ou colidem] → [o que fica]
Tom: Como narrar uma cena de filme sem mostrar as imagens.
Exemplos de primeiras legendas BOAS:
'Ela sabe que ele está mentindo — e canta assim mesmo'
'Duas vozes que se amam e se destroem ao mesmo tempo'
'Este é o dueto mais doloroso da história da ópera — e você vai entender por quê'
PROIBIDO: 'lindas vozes em harmonia', 'perfeita combinação', qualquer elogio de conjunto""",
    },
    "reacao_impacto_visual": {
        "label": "Reação / Impacto Visual",
        "emoji": "😱",
        "prompt": """Foque no IMPACTO FÍSICO E IMEDIATO desta performance no ouvinte —
o que acontece no corpo, no rosto, na reação involuntária de quem ouve.
Use o vídeo e a performance visível como gancho para prender quem está scrollando.
Estrutura: [o que o olho vê primeiro] → [o que está prestes a acontecer] → [a reação inevitável]
Tom: Direto, presente, quase agressivo na atenção. Como parar um scroll.
Exemplos de primeiras legendas BOAS:
'Olha a expressão dela quando a nota chega'
'A plateia não conseguiu ficar quieta — assista até o fim'
'Pare o que você está fazendo. Agora.'
PROIBIDO: 'performance incrível', 'que momento', qualquer reação genérica""",
    },
    "conexao_cultural": {
        "label": "Conexão Cultural",
        "emoji": "🌍",
        "prompt": """Foque em como esta música atravessa fronteiras — como ela existe
em culturas, épocas ou contextos completamente diferentes do original.
Filmes, funerais de estado, protestos, estádios, memórias coletivas.
Onde esta música apareceu que ninguém esperava — e o que isso revela.
Estrutura: [o contexto original] → [onde ela reapareceu de forma inesperada] → [o que isso diz]
Tom: Como descobrir que algo que você conhece tem uma vida secreta.
Exemplos de primeiras legendas BOAS:
'Esta música foi tocada em 4 funerais de chefes de estado'
'Você já ouviu isto — mas não sabia que era ópera'
'De Verdi para o cinema de Kubrick: a mesma nota, séculos depois'
PROIBIDO: 'conhecida no mundo todo', 'atravessa gerações', qualquer generalização cultural""",
    },
    "prefiro_escrever": {
        "label": "Prefiro Escrever",
        "emoji": "✏️",
        "prompt": "",
    },
}
