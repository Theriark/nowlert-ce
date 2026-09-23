"""TLS-only outbound SMTP delivery for the Email destination."""

from __future__ import annotations

import smtplib
import socket
import ssl
from email.message import EmailMessage

from models import Notification
from outputs.platform_common import decode_secret, notification_context, validate_network_host
from outputs.settings import normalize_output_settings
from storage.delivery import DeliveryResult


class EmailOutput:
    def __init__(self, *, smtp_factory=smtplib.SMTP, smtp_ssl_factory=smtplib.SMTP_SSL,
                 resolver=socket.getaddrinfo, tls_context_factory=ssl.create_default_context,
                 timeout: int = 15):
        self.smtp_factory = smtp_factory
        self.smtp_ssl_factory = smtp_ssl_factory
        self.resolver = resolver
        self.tls_context_factory = tls_context_factory
        self.timeout = int(timeout)

    def preview(self, settings: dict, notification: Notification) -> dict:
        normalized = normalize_output_settings("email", settings)
        message = self._message(normalized, notification)
        return {
            "from": normalized["from_address"], "to": list(normalized["to"]),
            "cc": list(normalized["cc"]), "reply_to": normalized["reply_to"],
            "subject": str(message["Subject"] or ""), "text": message.get_content(),
            "transport": "smtp", "security": normalized["security"],
        }

    def deliver(self, settings: dict, secret_value: bytes | None,
                notification: Notification) -> DeliveryResult:
        try:
            normalized = normalize_output_settings("email", settings)
            validate_network_host(
                normalized["server"], normalized["port"],
                allow_private_network=normalized["allow_private_network"],
                resolver=self.resolver,
            )
            credentials = decode_secret(secret_value)
            username = normalized["username"]
            password = str(credentials.get("password") or credentials.get("value") or "")
            if username and not password:
                return DeliveryResult(False, error_code="smtp_credentials_missing",
                                      safe_error="SMTP authentication is configured but the password is missing.")
            message = self._message(normalized, notification)
            recipients = [*normalized["to"], *normalized["cc"]]
            context = self.tls_context_factory()
            if normalized["security"] == "tls":
                client = self.smtp_ssl_factory(normalized["server"], normalized["port"],
                                               timeout=self.timeout, context=context)
            else:
                client = self.smtp_factory(normalized["server"], normalized["port"],
                                           timeout=self.timeout)
            with client:
                if normalized["security"] == "starttls":
                    client.ehlo()
                    client.starttls(context=context)
                    client.ehlo()
                if username:
                    client.login(username, password)
                refused = client.send_message(
                    message, from_addr=normalized["from_address"], to_addrs=recipients
                )
                if refused:
                    return DeliveryResult(
                        False, error_code="smtp_partial_recipient_rejection",
                        safe_error="SMTP accepted only some recipients. Nowlert will not retry automatically to avoid duplicate email.",
                    )
            return DeliveryResult(True)
        except smtplib.SMTPAuthenticationError:
            return DeliveryResult(False, error_code="smtp_authentication_failed",
                                  safe_error="SMTP authentication failed.")
        except smtplib.SMTPNotSupportedError:
            return DeliveryResult(False, error_code="smtp_tls_unavailable",
                                  safe_error="The SMTP server does not support the configured TLS mode.")
        except smtplib.SMTPRecipientsRefused as error:
            return _recipient_failure(error.recipients)
        except smtplib.SMTPResponseException as error:
            return _smtp_status_failure(error.smtp_code)
        except ssl.SSLError:
            return DeliveryResult(False, error_code="smtp_tls_failed",
                                  safe_error="SMTP TLS negotiation or certificate validation failed.")
        except (smtplib.SMTPServerDisconnected, TimeoutError, OSError):
            return DeliveryResult(False, retryable=True, error_code="smtp_transport_error",
                                  safe_error="The SMTP server could not be reached or disconnected.")
        except (TypeError, ValueError):
            return DeliveryResult(False, error_code="invalid_destination",
                                  safe_error="The Email destination configuration is invalid.")
        except smtplib.SMTPException:
            return DeliveryResult(False, error_code="smtp_error",
                                  safe_error="The SMTP server rejected the delivery.")
        except Exception:
            return DeliveryResult(False, error_code="smtp_delivery_exception",
                                  safe_error="The Email destination could not complete delivery.")

    @staticmethod
    def _message(settings: dict, notification: Notification) -> EmailMessage:
        context = notification_context(notification)
        message = EmailMessage()
        message["From"] = settings["from_address"]
        message["To"] = ", ".join(settings["to"])
        if settings["cc"]:
            message["Cc"] = ", ".join(settings["cc"])
        if settings["reply_to"]:
            message["Reply-To"] = settings["reply_to"]
        message["Subject"] = context["title"] or "Nowlert notification"
        body = context["body"] or context["title"] or "Nowlert notification"
        message.set_content("\n".join([
            body, "", f"Severity: {context['severity'] or 'information'}",
            f"Status: {context['status'] or 'information'}",
            f"Source: {context['source'] or 'nowlert'}",
            f"Category: {context['category'] or 'event'}",
            f"Event ID: {context['event_id']}",
        ]), charset="utf-8")
        return message


def _smtp_status_failure(code) -> DeliveryResult:
    try:
        status = int(code)
    except (TypeError, ValueError):
        status = 0
    if 400 <= status <= 499:
        return DeliveryResult(False, retryable=True, error_code="smtp_temporary_failure",
                              safe_error="The SMTP server returned a temporary failure.")
    return DeliveryResult(False, error_code="smtp_rejected",
                          safe_error="The SMTP server rejected the message.")


def _recipient_failure(recipients) -> DeliveryResult:
    codes = []
    if isinstance(recipients, dict):
        for value in recipients.values():
            if isinstance(value, (tuple, list)) and value:
                try:
                    codes.append(int(value[0]))
                except (TypeError, ValueError):
                    pass
    retryable = bool(codes) and all(400 <= code <= 499 for code in codes)
    return DeliveryResult(
        False, retryable=retryable,
        error_code="smtp_temporary_recipient_failure" if retryable else "smtp_recipient_rejected",
        safe_error="The SMTP server temporarily rejected every recipient." if retryable else "The SMTP server rejected every recipient.",
    )
