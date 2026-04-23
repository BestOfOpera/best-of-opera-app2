/**
 * Constantes editoriais do pipeline Reels Classics (RC).
 *
 * Fonte de verdade para limites visuais na UI do redator.
 * Alinhado com backend:
 *   - app-redator/backend/services/claude_service.py:_enforce_line_breaks_rc (default=38)
 *   - app-redator/backend/services/translate_service.py:_OVERLAY_LINE_LIMIT (pt/en=38)
 *   - app-editor DB editor_perfis RC.overlay_max_chars_linha=38 (via Ed-MIG1)
 *   - app-redator/backend/prompts/rc_overlay_prompt.py (instrução "38 CARACTERES POR LINHA")
 *
 * Migração 33→38 aplicada na Fase 3 (commit 90add64, 2026-04-22).
 * Backend migrado imediatamente; frontend (este arquivo) migrado em correção posterior.
 */

export const RC_MAX_CHARS_PER_LINE = 38
