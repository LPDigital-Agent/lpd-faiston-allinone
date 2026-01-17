# =============================================================================
# DebugAgent Tool: analyze_error
# =============================================================================
# Deep error analysis with root cause identification.
# Combines pattern matching, documentation search, and LLM reasoning.
#
# Analysis Strategy:
# 1. Generate error signature for pattern matching
# 2. Query AgentCore Memory for similar patterns
# 3. Search documentation via MCP gateways
# 4. Apply LLM reasoning for root cause analysis
#
# Output:
# - Technical explanation (pt-BR)
# - Root causes with confidence levels
# - Debugging steps
# - Documentation links
# - Similar patterns
# =============================================================================

import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Error categories for classification
ERROR_CATEGORIES = {
    "ValidationError": {"recoverable": False, "category": "validation"},
    "KeyError": {"recoverable": False, "category": "validation"},
    "ValueError": {"recoverable": False, "category": "validation"},
    "TypeError": {"recoverable": False, "category": "validation"},
    "TimeoutError": {"recoverable": True, "category": "network"},
    "ConnectionError": {"recoverable": True, "category": "network"},
    "OSError": {"recoverable": True, "category": "system"},
    "PermissionError": {"recoverable": False, "category": "permission"},
    "FileNotFoundError": {"recoverable": False, "category": "resource"},
    "ResourceExhausted": {"recoverable": True, "category": "resource"},
    "RateLimitError": {"recoverable": True, "category": "rate_limit"},
}


def generate_error_signature(
    error_type: str,
    message: str,
    operation: str,
) -> str:
    """
    Generate unique signature for error pattern matching.

    Signature is based on:
    - Error type (class name)
    - Normalized message (stripped of variable content)
    - Operation name

    Args:
        error_type: Exception class name
        message: Error message
        operation: Operation that failed

    Returns:
        Hash-based error signature
    """
    # Normalize message by removing variable content
    normalized_msg = message.lower()
    # Remove UUIDs
    import re
    normalized_msg = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "<UUID>",
        normalized_msg,
    )
    # Remove timestamps
    normalized_msg = re.sub(
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
        "<TIMESTAMP>",
        normalized_msg,
    )
    # Remove numbers
    normalized_msg = re.sub(r"\d+", "<NUM>", normalized_msg)

    # Create signature
    content = f"{error_type}:{operation}:{normalized_msg}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def classify_error(error_type: str) -> Dict[str, Any]:
    """
    Classify error by type.

    Args:
        error_type: Exception class name

    Returns:
        Classification dict with recoverable status and category
    """
    # Direct match
    if error_type in ERROR_CATEGORIES:
        return ERROR_CATEGORIES[error_type]

    # Pattern matching for common suffixes
    if error_type.endswith("Error"):
        base = error_type[:-5]
        for known_type, info in ERROR_CATEGORIES.items():
            if base in known_type:
                return info

    # Default: non-recoverable, unknown category
    return {"recoverable": False, "category": "unknown"}


async def analyze_error_tool(
    error_type: str,
    message: str,
    operation: str,
    stack_trace: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    recoverable: Optional[bool] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze error with deep reasoning and pattern matching.

    This is the primary analysis function that combines:
    1. Error signature generation
    2. Pattern matching from memory
    3. Documentation search
    4. LLM-based root cause analysis

    Args:
        error_type: Exception class name
        message: Error message text
        operation: Operation that failed
        stack_trace: Optional stack trace
        context: Optional additional context
        recoverable: Whether error is potentially recoverable
        session_id: Session ID for context

    Returns:
        Comprehensive analysis result
    """
    logger.info(f"[analyze_error] Starting analysis: {error_type} in {operation}")

    # Step 1: Generate error signature
    signature = generate_error_signature(error_type, message, operation)
    logger.debug(f"[analyze_error] Generated signature: {signature}")

    # Step 2: Classify error
    classification = classify_error(error_type)
    is_recoverable = recoverable if recoverable is not None else classification["recoverable"]

    # Step 3: Query memory for similar patterns
    similar_patterns = []
    try:
        from agents.specialists.debug.tools.query_memory_patterns import query_memory_patterns_tool

        memory_result = await query_memory_patterns_tool(
            error_signature=signature,
            error_type=error_type,
            operation=operation,
            max_patterns=3,
            session_id=session_id,
        )
        if memory_result.get("success"):
            similar_patterns = memory_result.get("patterns", [])
    except Exception as e:
        logger.warning(f"[analyze_error] Memory query failed: {e}")

    # Step 4: Search documentation (if no patterns found)
    documentation_links = []
    if not similar_patterns:
        try:
            from agents.specialists.debug.tools.search_documentation import search_documentation_tool

            doc_result = await search_documentation_tool(
                query=f"{error_type} {operation} {message[:50]}",
                sources=["aws", "agentcore"],
                max_results=3,
                session_id=session_id,
            )
            if doc_result.get("success"):
                documentation_links = doc_result.get("results", [])
        except Exception as e:
            logger.warning(f"[analyze_error] Documentation search failed: {e}")

    # Step 5: Build root causes based on analysis
    root_causes = _analyze_root_causes(
        error_type=error_type,
        message=message,
        operation=operation,
        stack_trace=stack_trace,
        context=context,
        similar_patterns=similar_patterns,
    )

    # Step 6: Generate debugging steps
    debugging_steps = _generate_debugging_steps(
        error_type=error_type,
        operation=operation,
        classification=classification,
        similar_patterns=similar_patterns,
    )

    # Step 7: Build technical explanation
    technical_explanation = _build_technical_explanation(
        error_type=error_type,
        message=message,
        operation=operation,
        classification=classification,
    )

    # Step 8: Determine suggested action
    suggested_action = _determine_suggested_action(
        is_recoverable=is_recoverable,
        classification=classification,
        similar_patterns=similar_patterns,
    )

    return {
        "success": True,
        "error_signature": signature,
        "error_type": error_type,
        "technical_explanation": technical_explanation,
        "root_causes": root_causes,
        "debugging_steps": debugging_steps,
        "documentation_links": documentation_links,
        "similar_patterns": similar_patterns,
        "recoverable": is_recoverable,
        "suggested_action": suggested_action,
        "analysis_timestamp": datetime.utcnow().isoformat() + "Z",
        "classification": classification,
    }


def _analyze_root_causes(
    error_type: str,
    message: str,
    operation: str,
    stack_trace: Optional[str],
    context: Optional[Dict[str, Any]],
    similar_patterns: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Analyze potential root causes.

    Args:
        error_type: Exception class name
        message: Error message
        operation: Operation that failed
        stack_trace: Optional stack trace
        context: Optional context
        similar_patterns: Patterns from memory

    Returns:
        List of root causes with confidence
    """
    root_causes = []

    # If we have similar patterns with resolutions, use them
    if similar_patterns:
        for pattern in similar_patterns[:2]:
            if pattern.get("resolution"):
                root_causes.append({
                    "cause": f"Padrão histórico: {pattern.get('resolution', 'Unknown')}",
                    "confidence": min(0.9, pattern.get("similarity", 0.5) + 0.1),
                    "evidence": [f"Padrão similar encontrado: {pattern.get('pattern_id', 'N/A')}"],
                    "source": "memory_pattern",
                })

    # Analyze based on error type
    error_lower = error_type.lower()
    message_lower = message.lower()

    if "validation" in error_lower or "key" in error_lower:
        root_causes.append({
            "cause": "Dados de entrada inválidos ou campo obrigatório ausente",
            "confidence": 0.8,
            "evidence": [f"Tipo de erro: {error_type}", f"Mensagem: {message[:100]}"],
            "source": "error_analysis",
        })

    if "timeout" in error_lower or "timeout" in message_lower:
        root_causes.append({
            "cause": "Timeout de rede ou serviço lento",
            "confidence": 0.85,
            "evidence": ["Indicador de timeout detectado na mensagem"],
            "source": "error_analysis",
        })

    if "connection" in error_lower or "connection" in message_lower:
        root_causes.append({
            "cause": "Falha de conexão com serviço externo",
            "confidence": 0.8,
            "evidence": ["Erro de conexão detectado"],
            "source": "error_analysis",
        })

    if "permission" in error_lower or "access" in message_lower or "denied" in message_lower:
        root_causes.append({
            "cause": "Permissão insuficiente para a operação",
            "confidence": 0.85,
            "evidence": ["Indicador de permissão/acesso na mensagem"],
            "source": "error_analysis",
        })

    # If no specific causes found, add generic one
    if not root_causes:
        root_causes.append({
            "cause": f"Erro durante operação {operation}",
            "confidence": 0.5,
            "evidence": [f"Análise baseada em: {error_type}"],
            "source": "fallback_analysis",
        })

    return root_causes


def _generate_debugging_steps(
    error_type: str,
    operation: str,
    classification: Dict[str, Any],
    similar_patterns: List[Dict[str, Any]],
) -> List[str]:
    """
    Generate debugging steps based on error analysis.

    Args:
        error_type: Exception class name
        operation: Operation that failed
        classification: Error classification
        similar_patterns: Patterns from memory

    Returns:
        List of debugging steps
    """
    steps = []

    # Add steps from similar patterns
    if similar_patterns:
        for pattern in similar_patterns[:1]:
            if pattern.get("debugging_steps"):
                steps.extend(pattern["debugging_steps"][:2])

    # Category-specific steps
    category = classification.get("category", "unknown")

    if category == "validation":
        steps.extend([
            "1. Verifique os dados de entrada no payload da requisição",
            "2. Confirme que todos os campos obrigatórios estão presentes",
            "3. Valide os tipos de dados (strings, números, datas)",
        ])
    elif category == "network":
        steps.extend([
            "1. Verifique a conectividade de rede com o serviço",
            "2. Aumente o timeout se necessário",
            "3. Implemente retry com backoff exponencial",
        ])
    elif category == "permission":
        steps.extend([
            "1. Verifique as permissões IAM do agente",
            "2. Confirme as políticas de acesso ao recurso",
            "3. Valide o token de autenticação",
        ])
    elif category == "resource":
        steps.extend([
            "1. Verifique se o recurso existe",
            "2. Confirme o path/identificador do recurso",
            "3. Verifique permissões de acesso ao recurso",
        ])
    else:
        steps.extend([
            "1. Analise os logs do agente para mais contexto",
            "2. Verifique o estado do serviço dependente",
            "3. Consulte a documentação da operação",
        ])

    # Remove duplicates while preserving order
    seen = set()
    unique_steps = []
    for step in steps:
        if step not in seen:
            seen.add(step)
            unique_steps.append(step)

    return unique_steps[:5]  # Limit to 5 steps


def _build_technical_explanation(
    error_type: str,
    message: str,
    operation: str,
    classification: Dict[str, Any],
) -> str:
    """
    Build technical explanation in Portuguese.

    Args:
        error_type: Exception class name
        message: Error message
        operation: Operation that failed
        classification: Error classification

    Returns:
        Technical explanation in pt-BR
    """
    category = classification.get("category", "unknown")
    recoverable = classification.get("recoverable", False)

    category_pt = {
        "validation": "validação de dados",
        "network": "comunicação de rede",
        "permission": "permissões de acesso",
        "resource": "recurso não encontrado",
        "rate_limit": "limite de requisições",
        "system": "sistema operacional",
        "unknown": "erro desconhecido",
    }.get(category, "erro")

    recovery_pt = "recuperável (pode ser resolvido com retry)" if recoverable else "não recuperável (requer correção manual)"

    return (
        f"Erro de {category_pt} durante a operação '{operation}'. "
        f"Tipo: {error_type}. "
        f"Este erro é {recovery_pt}. "
        f"Mensagem original: {message[:200]}"
    )


def _determine_suggested_action(
    is_recoverable: bool,
    classification: Dict[str, Any],
    similar_patterns: List[Dict[str, Any]],
) -> str:
    """
    Determine suggested action based on analysis.

    Args:
        is_recoverable: Whether error is recoverable
        classification: Error classification
        similar_patterns: Patterns from memory

    Returns:
        Suggested action: retry, fallback, escalate, or abort
    """
    # If similar pattern has high success rate, suggest retry
    if similar_patterns:
        for pattern in similar_patterns:
            if pattern.get("success_rate", 0) > 0.8:
                return "retry"

    # Based on recoverability
    if is_recoverable:
        return "retry"

    # Based on category
    category = classification.get("category", "unknown")
    if category in ["permission", "resource"]:
        return "escalate"
    if category == "validation":
        return "abort"

    return "fallback"
