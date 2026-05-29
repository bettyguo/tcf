"""Localized error message catalog (ADR-014 + master prompt §6.3).

Keys are stable; codes (`E_*_NNN`) map to keys via the `message_key`
class attribute on each `TCFAccelError` subclass.

Phase 2 ships EN + FR per master prompt §6.3. Other locales (es, ar, zh)
land in Phase 8 with the i18n system; the contract is "add a locale by
adding a column to each row," not "edit every error class."

A unit test (`tests/unit/test_error_messages.py`) verifies every key
used by an active error class has at least `en` and `fr` entries.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

Locale = str  # BCP-47-ish: "en", "fr", "es", "ar", "zh"

MESSAGES: Final[Mapping[str, Mapping[Locale, str]]] = {
    # ─── Base / generic ───────────────────────────────
    "base": {
        "en": "An internal error occurred.",
        "fr": "Une erreur interne s'est produite.",
    },
    # ─── Content domain ───────────────────────────────
    "content.not_available": {
        "en": "No items match the requested constraints: {constraints}.",
        "fr": "Aucun élément ne correspond aux critères demandés : {constraints}.",
    },
    "content.item_retired": {
        "en": "This item has been retired and is no longer available.",
        "fr": "Cet élément a été retiré et n'est plus disponible.",
    },
    "content.ingest_source_unavailable": {
        "en": "Content source {source} is unreachable: {detail}.",
        "fr": "La source de contenu {source} est inaccessible : {detail}.",
    },
    "content.llm_unreliable": {
        "en": "The {role} LLM ({model}) failed to produce valid output after {attempts} attempts.",
        "fr": "Le modèle {role} ({model}) n'a pas produit de sortie valide après {attempts} tentatives.",
    },
    "content.cefr_unavailable": {
        "en": "The CEFR classifier ({version}) is unavailable: {detail}.",
        "fr": "Le classifieur CEFR ({version}) est indisponible : {detail}.",
    },
    "content.distribution_violation": {
        "en": "Bank distribution violates quota cell {cell}: actual={actual:.2%}, target={target:.2%}, tolerance={tolerance:.2%}.",
        "fr": "La distribution de la banque viole la cellule {cell} : actuel={actual:.2%}, cible={target:.2%}, tolérance={tolerance:.2%}.",
    },
    "content.ingest_license_missing": {
        "en": "Ingested asset {source}:{source_id} is missing its license.json sidecar.",
        "fr": "L'élément ingéré {source}:{source_id} n'a pas de fichier license.json associé.",
    },
    "content.ingest_license_incompatible": {
        "en": "License {license} for {source}:{source_id} is not in the redistribution allowlist.",
        "fr": "La licence {license} pour {source}:{source_id} n'est pas dans la liste autorisée pour la redistribution.",
    },
    # ─── Scheduler domain ─────────────────────────────
    "scheduler.generic": {
        "en": "The scheduler encountered an error: {detail}.",
        "fr": "Le planificateur a rencontré une erreur : {detail}.",
    },
    "scheduler.cache_miss": {
        "en": "The schedule for ({user_id_hashed}, {module}) is being recomputed. Try again shortly.",
        "fr": "Le planning pour ({user_id_hashed}, {module}) est en cours de recalcul. Veuillez réessayer sous peu.",
    },
    # ─── Scoring domain ───────────────────────────────
    "scoring.generic": {
        "en": "Scoring failed: {detail}.",
        "fr": "L'évaluation a échoué : {detail}.",
    },
    "scoring.asr_low_confidence": {
        "en": "We couldn't transcribe the audio confidently (score={score:.2f}, threshold={threshold:.2f}). Please re-record in a quieter setting.",
        "fr": "Nous n'avons pas pu transcrire l'audio avec assez de confiance (score={score:.2f}, seuil={threshold:.2f}). Veuillez réenregistrer dans un environnement plus calme.",
    },
    "scoring.text_too_short": {
        "en": "Your response is {word_count} words; this task expects at least {minimum}.",
        "fr": "Votre réponse fait {word_count} mots ; cette tâche en attend au moins {minimum}.",
    },
    "scoring.audio_too_short": {
        "en": "Your recording is {duration_s:.1f} seconds; this task expects at least {minimum_s} seconds.",
        "fr": "Votre enregistrement dure {duration_s:.1f} secondes ; cette tâche en attend au moins {minimum_s}.",
    },
    "scoring.rubric_mismatch": {
        "en": "The submitted item is for rubric {item_rubric}, but the scorer was loaded for {loaded_rubric}.",
        "fr": "L'élément soumis utilise la grille {item_rubric}, mais l'évaluateur chargé concerne {loaded_rubric}.",
    },
    # ─── Calibration domain ───────────────────────────
    "calibration.generic": {
        "en": "Calibration failed: {detail}.",
        "fr": "Le calibrage a échoué : {detail}.",
    },
    "calibration.insufficient_obs": {
        "en": "Not enough data yet to estimate confidently — complete {needed} more items (currently {have}).",
        "fr": "Pas encore assez de données pour estimer avec confiance — complétez {needed} éléments de plus (actuellement {have}).",
    },
    # ─── Auth domain ──────────────────────────────────
    "auth.generic": {
        "en": "Authentication required.",
        "fr": "Authentification requise.",
    },
    "auth.invalid_credentials": {
        "en": "Invalid email or password.",
        "fr": "Adresse e-mail ou mot de passe invalide.",
    },
    "auth.token_expired": {
        "en": "Your session has expired. Please sign in again.",
        "fr": "Votre session a expiré. Veuillez vous reconnecter.",
    },
    "auth.token_invalid": {
        "en": "The authentication token is invalid.",
        "fr": "Le jeton d'authentification est invalide.",
    },
    "auth.forbidden": {
        "en": "You do not have permission to perform this action.",
        "fr": "Vous n'avez pas la permission d'effectuer cette action.",
    },
    # ─── Validation / rate-limit ──────────────────────
    "validation.request_body": {
        "en": "The request body is invalid: {detail}.",
        "fr": "Le corps de la requête est invalide : {detail}.",
    },
    "rate_limit.exceeded": {
        "en": "You are sending requests too quickly. Please wait {retry_after_s} seconds.",
        "fr": "Vous envoyez trop de requêtes trop rapidement. Veuillez patienter {retry_after_s} secondes.",
    },
    # ─── Session domain (Phase 5) ─────────────────────
    "session.exam_shape_floor": {
        "en": "You haven't done an exam-shape session this week ({minutes} of {floor} min). Start one, or dismiss this week.",
        "fr": "Vous n'avez pas fait de session en conditions d'examen cette semaine ({minutes} sur {floor} min). Commencez-en une, ou ignorez pour cette semaine.",
    },
    "session.pause_expired": {
        "en": "This paused session expired ({hours} h since pause; limit is 24 h). Please start a new session.",
        "fr": "Cette session en pause a expiré ({hours} h depuis la pause ; la limite est de 24 h). Veuillez démarrer une nouvelle session.",
    },
    "session.accessibility_required": {
        "en": "The requested drill ({drill_kind}) needs an accessibility setting you haven't enabled. Update your profile to continue.",
        "fr": "L'exercice demandé ({drill_kind}) nécessite un réglage d'accessibilité que vous n'avez pas activé. Mettez à jour votre profil pour continuer.",
    },
    "session.drill_input_invalid": {
        "en": "Your response for this drill is invalid: {detail}.",
        "fr": "Votre réponse pour cet exercice est invalide : {detail}.",
    },
    # ─── ASR / Pronunciation / TTS / LLM (Phase 5) ────
    "asr.backend_unavailable": {
        "en": "The speech-recognition backend ({backend}) is unavailable: {detail}.",
        "fr": "Le moteur de reconnaissance vocale ({backend}) est indisponible : {detail}.",
    },
    "pronunciation.pipeline_failure": {
        "en": "Pronunciation feedback couldn't be computed for this recording; the rest of your result is unaffected.",
        "fr": "Le retour sur la prononciation n'a pas pu être calculé pour cet enregistrement ; le reste de votre résultat n'est pas affecté.",
    },
    "tts.backend_unavailable": {
        "en": "The examiner voice (text-to-speech) is unavailable: {detail}.",
        "fr": "La voix de l'examinateur (synthèse vocale) est indisponible : {detail}.",
    },
    "llm.backend_unavailable": {
        "en": "The language-model gateway is unavailable: {detail}.",
        "fr": "La passerelle du modèle de langage est indisponible : {detail}.",
    },
    # ─── Mock exam (Phase 6) ──────────────────────────
    "mock.cadence_exceeded": {
        "en": "Mock-exam cadence cap reached: {reason}",
        "fr": "Cadence de l'examen blanc dépassée : {reason}",
    },
    "mock.forfeited": {
        "en": "This mock has been forfeited and cannot be resumed.",
        "fr": "Cet examen blanc a été abandonné et ne peut pas être repris.",
    },
    "mock.not_scored": {
        "en": "This mock has not been scored yet (current state: {state}).",
        "fr": "Cet examen blanc n'a pas encore été noté (état actuel : {state}).",
    },
    "mock.invalid_transition": {
        "en": "Illegal mock-exam transition from {from_state} via {event}: {detail}",
        "fr": "Transition illégale de l'examen blanc depuis {from_state} via {event} : {detail}",
    },
    "mock.co_single_play": {
        "en": "CO audio items may be played only once per mock (item {item_id}).",
        "fr": "Les éléments audio CO ne peuvent être lus qu'une seule fois par examen blanc (élément {item_id}).",
    },
    # ─── Phase 2 stub ─────────────────────────────────
    "not_implemented": {
        "en": "This route is not yet implemented (owned by phase {phase}).",
        "fr": "Cette route n'est pas encore implémentée (responsable : phase {phase}).",
    },
}


def render(key: str, locale: Locale, /, **context: object) -> str:
    """Render a localized message.

    Falls back to English if the requested locale is missing the key.
    Renders without raising on missing context keys (the message embeds
    `[render_error=...]` so the caller can still log something useful).

    Example:
        >>> render("scoring.text_too_short", "fr", word_count=20, minimum=60)
        'Votre réponse fait 20 mots ; cette tâche en attend au moins 60.'

    Complexity: O(1) lookup + O(format-string length).
    """
    bundle = MESSAGES.get(key, {})
    template = bundle.get(locale) or bundle.get("en") or f"[missing-message-key: {key}]"
    try:
        return template.format(**context)
    except (KeyError, IndexError) as exc:  # missing placeholder
        return f"{template} [render_error={exc!s}]"


__all__ = ["MESSAGES", "Locale", "render"]
