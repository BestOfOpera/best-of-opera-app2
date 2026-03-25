-- SPEC-008 — T1: Corrigir overlay_style do perfil RC no banco
-- Execute no Railway (PostgreSQL)

-- PASSO 1: Verificar estado atual
SELECT sigla, overlay_style, lyrics_style, traducao_style, font_name
FROM perfis
WHERE sigla = 'RC';

-- PASSO 2: Atualizar para Brand Definition RC v1.0
UPDATE perfis
SET
  overlay_style = '{"fontname":"Inter Bold","fontsize":48,"gancho_fontsize":52,"corpo_fontsize":48,"cta_fontsize":44,"primary_colour":"&H00FFFFFF","outline":0,"shadow":0,"alignment":2,"margin_v":28}',
  lyrics_style = '{}',
  traducao_style = '{}',
  font_name = 'Inter Bold'
WHERE sigla = 'RC';

-- PASSO 3: Confirmar resultado
SELECT sigla, overlay_style, font_name
FROM perfis
WHERE sigla = 'RC';
