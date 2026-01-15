# =============================================================================
# Postal Service Adapter (Real API Integration)
# =============================================================================
"""
Real shipping adapter that integrates with postal service APIs.

This adapter provides:
- Quotes: via Correios Public API (no posting created)
- Shipments: via PostarObjeto REST API
- Tracking: via GetSituacaoPostagem REST API
- Labels: via ImpressaoRemota HTTP API
- Liberation: via LiberarDownloadConhecimento SOAP API

Credentials are retrieved from AWS Secrets Manager (production) with fallback
to environment variables (local development).

Secret ARN: faiston-one/postal/credentials
Secret Format: {"usuario": "...", "token": "...", "id_perfil": "..."}
"""

import json
import os
import logging
import re
import httpx
from functools import lru_cache
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

import boto3
from botocore.exceptions import ClientError

from .base import (
    ShippingAdapter,
    QuoteResult,
    ShipmentResult,
    TrackingResult,
    TrackingEvent,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Credentials Management
# =============================================================================

# Secret ID in AWS Secrets Manager
POSTAL_SECRET_ID = "faiston-one/postal/credentials"


class PostalCredentialsError(Exception):
    """Raised when postal credentials cannot be retrieved or are invalid."""
    pass


@lru_cache(maxsize=1)
def get_postal_credentials() -> Dict[str, str]:
    """
    Retrieve postal API credentials from AWS Secrets Manager.

    Uses lru_cache for in-memory caching to avoid repeated API calls.
    Falls back to environment variables if Secrets Manager is unavailable
    (useful for local development).

    Returns:
        Dictionary with keys: usuario, token, id_perfil

    Raises:
        PostalCredentialsError: If credentials cannot be retrieved or are invalid
    """
    # Determine AWS region (explicit for AgentCore cold start reliability)
    region = os.environ.get(
        "AWS_REGION",
        os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
    )

    try:
        logger.info(f"[PostalCredentials] Fetching credentials from Secrets Manager: {POSTAL_SECRET_ID}")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=POSTAL_SECRET_ID)
        secret_data = json.loads(response["SecretString"])

        # Validate required fields
        required_fields = ["usuario", "token", "id_perfil"]
        missing_fields = [f for f in required_fields if not secret_data.get(f)]

        if missing_fields:
            raise PostalCredentialsError(
                f"Secret is missing required fields: {missing_fields}"
            )

        logger.info("[PostalCredentials] Successfully retrieved credentials from Secrets Manager")
        return {
            "usuario": secret_data["usuario"],
            "token": secret_data["token"],
            "id_perfil": secret_data["id_perfil"],
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(
            f"[PostalCredentials] Secrets Manager error ({error_code}): {e}. "
            "Falling back to environment variables."
        )
    except json.JSONDecodeError as e:
        logger.warning(
            f"[PostalCredentials] Failed to parse secret as JSON: {e}. "
            "Falling back to environment variables."
        )
    except Exception as e:
        logger.warning(
            f"[PostalCredentials] Unexpected error fetching secret: {e}. "
            "Falling back to environment variables."
        )

    # Fallback to environment variables (for local development)
    logger.info("[PostalCredentials] Using environment variable fallback")
    env_credentials = {
        "usuario": os.getenv("POSTAL_USUARIO"),
        "token": os.getenv("POSTAL_TOKEN"),
        "id_perfil": os.getenv("POSTAL_IDPERFIL"),
    }

    # Validate environment credentials
    missing_env = [k for k, v in env_credentials.items() if not v]
    if missing_env:
        raise PostalCredentialsError(
            f"Credentials not available. Missing environment variables: "
            f"{['POSTAL_' + k.upper() for k in missing_env]}. "
            f"Set these variables or ensure Secrets Manager access to {POSTAL_SECRET_ID}"
        )

    return env_credentials


def clear_credentials_cache() -> None:
    """
    Clear the cached credentials.

    Call this if credentials need to be refreshed (e.g., after rotation).
    """
    get_postal_credentials.cache_clear()
    logger.info("[PostalCredentials] Credentials cache cleared")


class PostalServiceAdapter(ShippingAdapter):
    """
    Real implementation for postal service integration.

    Uses Correios public API for quotes (free, no posting created)
    and middleware API for shipments, tracking, and labels.
    """

    # API Endpoints
    CORREIOS_QUOTE_URL = "https://www.correios.com.br/@@precosEPrazosView"
    POSTING_API_URL = "http://vpsrv.visualset.com.br/api/v1/middleware/PostarObjeto"
    TRACKING_API_URL = "http://vpsrv.visualset.com.br/api/v1/conhecimento/GetSituacaoPostagem"
    LABEL_API_URL = "https://vipp.visualset.com.br/vipp/remoto/ImpressaoRemota.php"
    SOAP_API_URL = "http://vpsrv.visualset.com.br/PostagemVipp.asmx"

    # Service codes
    # Service codes for Correios public API (@@precosEPrazosView)
    # These are the codProdutoAgencia values returned by the API
    SERVICE_SEDEX = "04014"
    SERVICE_PAC = "04510"
    SERVICE_SEDEX_10 = "40215"  # May not be available on all routes

    def __init__(
        self,
        usuario: Optional[str] = None,
        token: Optional[str] = None,
        id_perfil: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the postal service adapter.

        Credentials are loaded from AWS Secrets Manager (faiston-one/postal/credentials)
        with fallback to environment variables for local development.

        Args:
            usuario: API username (overrides Secrets Manager if provided)
            token: API password/token (overrides Secrets Manager if provided)
            id_perfil: Profile ID (overrides Secrets Manager if provided)
            timeout: HTTP request timeout in seconds

        Raises:
            PostalCredentialsError: If credentials cannot be retrieved
        """
        # Get credentials from Secrets Manager (with env var fallback)
        # Only fetch from Secrets Manager if no explicit credentials provided
        if usuario and token and id_perfil:
            # All credentials explicitly provided - use them directly
            self.usuario = usuario
            self.token = token
            self.id_perfil = id_perfil
            logger.info("[PostalServiceAdapter] Using explicitly provided credentials")
        else:
            # Fetch from Secrets Manager (cached)
            credentials = get_postal_credentials()
            self.usuario = usuario or credentials["usuario"]
            self.token = token or credentials["token"]
            self.id_perfil = id_perfil or credentials["id_perfil"]

        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"[PostalServiceAdapter] Initialized with profile {self.id_perfil}")

    @property
    def adapter_name(self) -> str:
        return "PostalServiceAdapter"

    @property
    def is_mock(self) -> bool:
        return False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def get_quotes(
        self,
        origin_cep: str,
        destination_cep: str,
        weight_grams: int,
        length_cm: int,
        width_cm: int,
        height_cm: int,
        declared_value: float,
    ) -> List[QuoteResult]:
        """
        Get quotes from Correios public API (no posting created).

        This uses the public pricing API which does NOT require
        authentication and does NOT create any postings.
        """
        logger.info(f"[PostalServiceAdapter] get_quotes: {origin_cep} -> {destination_cep}")

        # Clean CEP (remove formatting)
        origin_cep = origin_cep.replace("-", "").replace(".", "").strip()
        destination_cep = destination_cep.replace("-", "").replace(".", "").strip()

        # Convert weight to kg for Correios API
        weight_kg = weight_grams / 1000

        quotes = []
        services = [
            (self.SERVICE_SEDEX, "SEDEX"),
            (self.SERVICE_PAC, "PAC"),
            (self.SERVICE_SEDEX_10, "SEDEX 10"),
        ]

        client = await self._get_client()

        for service_code, service_name in services:
            try:
                params = {
                    "cepOrigem": origin_cep,
                    "cepDestino": destination_cep,
                    "peso": str(weight_kg),
                    "formato": "1",  # Box format
                    "comprimento": str(length_cm),
                    "altura": str(height_cm),
                    "largura": str(width_cm),
                    "servico": service_code,
                }

                response = await client.get(self.CORREIOS_QUOTE_URL, params=params)

                if response.status_code == 200:
                    data = response.json()

                    # Handle list response from Correios API
                    # The API returns ALL available services in a list, regardless of servico param
                    # We need to find the matching service by codProdutoAgencia
                    item = None
                    if isinstance(data, list):
                        for candidate in data:
                            if candidate.get("codProdutoAgencia") == service_code:
                                item = candidate
                                break
                        # If not found, service is not available for this route
                        if item is None:
                            quotes.append(QuoteResult(
                                carrier="Correios",
                                service=service_name,
                                service_code=service_code,
                                price=0,
                                delivery_days=0,
                                is_simulated=False,
                                available=False,
                                reason="Servico nao disponivel para esta rota",
                                raw_response=data,
                            ))
                            continue
                    else:
                        item = data

                    # Parse Correios response (@@precosEPrazosView format)
                    # Success: status == 200, price in "precoAgencia" (e.g., "R$ 40,40")
                    # Delivery in "prazo" (e.g., "1 dia útil" or "5 dias úteis")
                    if item.get("status") == 200:
                        # Parse price: "R$ 40,40" -> 40.40
                        price_str = item.get("precoAgencia", "R$ 0,00")
                        price_str = price_str.replace("R$", "").replace(" ", "").strip()
                        price_str = price_str.replace(".", "").replace(",", ".")
                        price = float(price_str) if price_str else 0.0

                        # Parse delivery days: "1 dia útil" or "5 dias úteis" -> extract number
                        prazo_str = item.get("prazo", "0 dias")
                        prazo_match = re.search(r"(\d+)", prazo_str)
                        delivery_days = int(prazo_match.group(1)) if prazo_match else 0

                        quotes.append(QuoteResult(
                            carrier="Correios",
                            service=service_name,
                            service_code=service_code,
                            price=price,
                            delivery_days=delivery_days,
                            delivery_date=(datetime.utcnow() + timedelta(days=delivery_days)).strftime("%Y-%m-%d"),
                            is_simulated=False,
                            available=True,
                            raw_response=data,
                        ))
                    else:
                        # Error case: status != 200 or msg contains error
                        error_msg = item.get("msg", "").strip()
                        if not error_msg or error_msg == " ":
                            error_msg = "Servico indisponivel"
                        quotes.append(QuoteResult(
                            carrier="Correios",
                            service=service_name,
                            service_code=service_code,
                            price=0,
                            delivery_days=0,
                            is_simulated=False,
                            available=False,
                            reason=error_msg,
                            raw_response=data,
                        ))

            except Exception as e:
                logger.warning(f"[PostalServiceAdapter] Quote error for {service_name}: {e}")
                quotes.append(QuoteResult(
                    carrier="Correios",
                    service=service_name,
                    service_code=service_code,
                    price=0,
                    delivery_days=0,
                    is_simulated=False,
                    available=False,
                    reason=f"Erro na consulta: {str(e)}",
                ))

        return quotes

    async def create_shipment(
        self,
        origin: Dict[str, Any],
        destination: Dict[str, Any],
        volumes: List[Dict[str, Any]],
        invoices: Optional[List[Dict[str, Any]]] = None,
        declared_value: float = 0.0,
        service_code: Optional[str] = None,
    ) -> ShipmentResult:
        """
        Create a shipment via PostarObjeto API.

        This CREATES a real posting with tracking code.
        The posting auto-expires in 15 days if not physically shipped.
        """
        logger.info(f"[PostalServiceAdapter] create_shipment to {destination.get('cidade')}")

        # Build request body
        request_body = {
            "PerfilVipp": {
                "Usuario": self.usuario,
                "Token": self.token,
                "IdPerfil": self.id_perfil,
            },
            "ContratoEct": {
                "NrContrato": "",
                "CodigoAdministrativo": "",
                "NrCartao": "",
            },
            "Destinatario": {
                "Nome": destination.get("nome", ""),
                "Endereco": destination.get("endereco", ""),
                "Numero": destination.get("numero", "S/N"),
                "Complemento": destination.get("complemento", ""),
                "Bairro": destination.get("bairro", ""),
                "Cidade": destination.get("cidade", ""),
                "UF": destination.get("uf", ""),
                "Cep": destination.get("cep", "").replace("-", ""),
                "Telefone": destination.get("telefone", ""),
                "Email": destination.get("email", ""),
            },
            "Volumes": [
                {
                    "Peso": str(vol.get("peso", 0)),
                    "Altura": str(vol.get("altura", 0)),
                    "Largura": str(vol.get("largura", 0)),
                    "Comprimento": str(vol.get("comprimento", 0)),
                    "ValorDeclarado": str(declared_value) if declared_value > 0 else "",
                }
                for vol in volumes
            ],
        }

        # Add invoices if provided
        if invoices:
            request_body["NotasFiscais"] = [
                {
                    "NrNotaFiscal": str(inv.get("numero", "")),
                    "DtNotaFiscal": inv.get("data", ""),
                    "VlrTotalNota": str(inv.get("valor", "")),
                }
                for inv in invoices
            ]

        try:
            client = await self._get_client()
            response = await client.post(
                self.POSTING_API_URL,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Accept-Encoding": "UTF-8",
                },
            )

            data = response.json()

            # Check for success
            if data.get("StatusPostagem") == "Valida":
                volume_data = data.get("Volumes", [{}])[0]

                return ShipmentResult(
                    success=True,
                    tracking_code=volume_data.get("Etiqueta", ""),
                    carrier="Correios",
                    service=volume_data.get("ServicoECT", "SEDEX"),
                    service_code=volume_data.get("CodigoFinanceiroECT", "04162"),
                    price=float(volume_data.get("ValorPostagem", 0) or 0),
                    delivery_days=int(volume_data.get("DiasUteisPrazo", 0) or 0),
                    estimated_delivery=(
                        datetime.utcnow() + timedelta(days=int(volume_data.get("DiasUteisPrazo", 0) or 0))
                    ).strftime("%Y-%m-%d"),
                    label_available=True,
                    is_simulated=False,
                    raw_response=data,
                )
            else:
                # Parse errors
                errors = []
                for err in data.get("ListaErros", []):
                    errors.append({
                        "type": err.get("TipoErro"),
                        "field": err.get("Campo"),
                        "message": err.get("Descricao"),
                    })

                return ShipmentResult(
                    success=False,
                    error_code="VALIDATION_ERROR",
                    error_message="Postagem invalida",
                    errors=errors,
                    is_simulated=False,
                    raw_response=data,
                )

        except Exception as e:
            logger.error(f"[PostalServiceAdapter] create_shipment error: {e}", exc_info=True)
            return ShipmentResult(
                success=False,
                error_code="API_ERROR",
                error_message=str(e),
                is_simulated=False,
            )

    async def track_shipment(
        self,
        tracking_code: str,
        full_details: bool = False,
    ) -> TrackingResult:
        """
        Track a shipment via GetSituacaoPostagem API.

        Note: Requires liberation first via liberate_shipment().
        """
        logger.info(f"[PostalServiceAdapter] track_shipment: {tracking_code}")

        try:
            client = await self._get_client()
            response = await client.get(
                self.TRACKING_API_URL,
                headers={
                    "Usuario": self.usuario,
                    "Senha": self.token,
                    "StDadosCompletos": "1" if full_details else "0",
                    "BuscarPor": "EtiquetaPostagem",
                },
                content=f'["{tracking_code}"]',
            )

            data = response.json()

            # Check if data found
            if not data or (isinstance(data, list) and len(data) == 0):
                return TrackingResult(
                    tracking_code=tracking_code,
                    carrier="Correios",
                    status="NOT_FOUND",
                    status_description="Objeto nao encontrado no sistema",
                    is_simulated=False,
                )

            # Parse first result
            item = data[0] if isinstance(data, list) else data

            events = []
            if item.get("DataDoUltimoStatus"):
                events.append(TrackingEvent(
                    timestamp=item["DataDoUltimoStatus"],
                    status=item.get("IdGrupoStatusAtual", ""),
                    description=item.get("DescricaoGrupoStatusAtual", ""),
                    location=item.get("LocalDoUltimoStatus", ""),
                ))

            return TrackingResult(
                tracking_code=tracking_code,
                carrier="Correios",
                status=item.get("IdGrupoStatusAtual", "UNKNOWN"),
                status_description=item.get("DescricaoGrupoStatusAtual", "Status desconhecido"),
                is_delivered=item.get("IdGrupoStatusAtual") == "ENTREGUE",
                estimated_delivery=item.get("DataEstimadaDeEntrega"),
                events=events,
                is_simulated=False,
                raw_response=item,
            )

        except Exception as e:
            logger.error(f"[PostalServiceAdapter] track_shipment error: {e}", exc_info=True)
            return TrackingResult(
                tracking_code=tracking_code,
                carrier="Correios",
                status="ERROR",
                status_description=f"Erro na consulta: {str(e)}",
                is_simulated=False,
            )

    async def get_label(
        self,
        tracking_code: str,
        format: str = "pdf",
    ) -> bytes:
        """
        Get shipping label via ImpressaoRemota API.

        Args:
            tracking_code: Tracking code for the label
            format: 'pdf' or 'zvp'
        """
        logger.info(f"[PostalServiceAdapter] get_label: {tracking_code}")

        # Map format to Saida code
        saida_map = {
            "pdf": "1",      # PDF 4x per page
            "pdf_6x": "2",   # PDF 6x per page
            "zvp": "0",      # ZVP format
        }
        saida = saida_map.get(format, "1")

        try:
            client = await self._get_client()
            response = await client.post(
                self.LABEL_API_URL,
                data={
                    "Usr": self.usuario,
                    "Pwd": self.token,
                    "Filtro": "4",  # Filter by PLP number
                    "Ordem": "0",
                    "Saida": saida,
                    "Lista": tracking_code,
                },
            )

            if response.status_code == 200 and response.content:
                return response.content
            else:
                raise Exception(f"Label generation failed: {response.status_code}")

        except Exception as e:
            logger.error(f"[PostalServiceAdapter] get_label error: {e}", exc_info=True)
            raise

    async def liberate_shipment(
        self,
        tracking_code: str,
    ) -> bool:
        """
        Liberate shipment for tracking via SOAP API.

        This is required before GetSituacaoPostagem returns data.
        """
        logger.info(f"[PostalServiceAdapter] liberate_shipment: {tracking_code}")

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:vis="http://www.visualset.inf.br/">
  <soap:Body>
    <vis:LiberarDownloadConhecimento>
      <vis:LiberarPostagem>
        <vis:PerfilVipp>
          <vis:Usuario>{self.usuario}</vis:Usuario>
          <vis:Token>{self.token}</vis:Token>
          <vis:IdPerfil>{self.id_perfil}</vis:IdPerfil>
        </vis:PerfilVipp>
        <vis:Etiqueta>{tracking_code}</vis:Etiqueta>
        <vis:StLiberado>1</vis:StLiberado>
      </vis:LiberarPostagem>
    </vis:LiberarDownloadConhecimento>
  </soap:Body>
</soap:Envelope>"""

        try:
            client = await self._get_client()
            response = await client.post(
                self.SOAP_API_URL,
                content=soap_body,
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://www.visualset.inf.br/LiberarDownloadConhecimento",
                },
            )

            # Parse SOAP response
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                # Look for StLiberado in response
                ns = {"vis": "http://www.visualset.inf.br/"}
                result = root.find(".//vis:StLiberado", ns)
                if result is not None and result.text == "1":
                    logger.info(f"[PostalServiceAdapter] Liberation successful: {tracking_code}")
                    return True

            logger.warning(f"[PostalServiceAdapter] Liberation failed: {tracking_code}")
            return False

        except Exception as e:
            logger.error(f"[PostalServiceAdapter] liberate_shipment error: {e}", exc_info=True)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check API connectivity."""
        try:
            client = await self._get_client()
            # Simple connectivity test to Correios public API
            response = await client.get(
                self.CORREIOS_QUOTE_URL,
                params={"cepOrigem": "01310100", "cepDestino": "01310100", "peso": "1", "servico": "04162"},
            )
            return {
                "healthy": response.status_code == 200,
                "adapter": self.adapter_name,
                "is_mock": False,
                "correios_api": response.status_code == 200,
            }
        except Exception as e:
            return {
                "healthy": False,
                "adapter": self.adapter_name,
                "is_mock": False,
                "error": str(e),
            }

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
