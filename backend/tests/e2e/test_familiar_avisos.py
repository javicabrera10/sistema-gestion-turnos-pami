"""Sprint 3 (JAVI123-8): los turnos le avisan al familiar autorizado, con datos mínimos."""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.patterns.canal_strategy import CanalSMS
from app.services.recordatorio_service import ahora_local

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")

FAMILIAR = {"nombre": "Marta Gómez", "parentesco": "Hija", "canal": "sms", "contacto": "+5492615551234", "consentimiento": True}
MOTIVO = "Me duele el pecho cuando camino"


def _futuro(dias: int = 7) -> str:
    fecha = datetime.now(timezone.utc) + timedelta(days=dias)
    return fecha.replace(hour=10, minute=30, second=0, microsecond=0, tzinfo=None).isoformat(timespec="seconds")


def _id_de(client, headers) -> str:
    return client.get("/api/auth/me", headers=headers).get_json()["id"]


@pytest.fixture
def h_paciente(auth_headers):
    return auth_headers(*PACIENTE)


@pytest.fixture
def h_medico(auth_headers):
    return auth_headers(*MEDICO)


@pytest.fixture
def h_admin(auth_headers):
    return auth_headers(*ADMIN)


@pytest.fixture
def autorizar(client, h_paciente):
    def _autorizar(**cambios):
        resp = client.put("/api/familiar", json={**FAMILIAR, **cambios}, headers=h_paciente)
        assert resp.status_code == 200
    return _autorizar


@pytest.fixture
def pedir_turno(client, h_paciente, h_admin, h_medico):
    """Devuelve una función que deja un turno otorgado (y confirmado si se pide)."""

    def _pedir(fecha=None, confirmar=False) -> str:
        fecha = fecha or _futuro()
        cuerpo = {"especialidad": "Cardiología", "fecha_hora": fecha, "motivo": MOTIVO}
        turno_id = client.post("/api/turnos", json=cuerpo, headers=h_paciente).get_json()["id"]
        otorgar = {"medico_id": _id_de(client, h_medico), "fecha_hora": fecha}
        assert client.patch(f"/api/turnos/{turno_id}/otorgar", json=otorgar, headers=h_admin).status_code == 200
        if confirmar:
            assert client.patch(f"/api/turnos/{turno_id}/confirmar", headers=h_paciente).status_code == 200
        return turno_id

    return _pedir


def _avisos(client, headers):
    return client.get("/api/familiar/avisos", headers=headers).get_json()


def _textos(client, headers):
    return [a["texto"] for a in _avisos(client, headers)]


# ---------- los avisos llegan ----------

def test_al_otorgar_un_turno_se_le_avisa_al_familiar(client, h_paciente, autorizar, pedir_turno):
    autorizar()
    pedir_turno()

    avisos = _avisos(client, h_paciente)

    assert len(avisos) == 1
    assert avisos[0]["canal"] == "sms"
    assert avisos[0]["destino"] == "+5492615551234"
    assert avisos[0]["evento"] == "turno.otorgado"
    assert avisos[0]["estado"] == "enviado (simulado)"
    assert avisos[0]["texto"].startswith("Paula tiene un turno médico otorgado para el ")
    assert avisos[0]["texto"].endswith("a las 10:30 hs.")


def test_el_mensaje_no_lleva_datos_clinicos_ni_el_apellido(client, h_paciente, autorizar, pedir_turno):
    autorizar()
    pedir_turno(confirmar=True)

    for aviso in _avisos(client, h_paciente):
        assert "Cardiología" not in aviso["texto"]
        assert "pecho" not in aviso["texto"]
        assert "Paciente" not in aviso["texto"]


def test_el_flujo_completo_del_turno_llega_al_familiar(client, h_paciente, h_admin, autorizar, pedir_turno):
    autorizar()
    turno_id = pedir_turno(confirmar=True)  # otorgado y confirmado
    client.patch(f"/api/turnos/{turno_id}/reprogramar", json={"fecha_hora": _futuro(20)}, headers=h_admin)
    client.patch(f"/api/turnos/{turno_id}/cancelar", headers=h_admin)

    eventos = [a["evento"] for a in _avisos(client, h_paciente)]

    assert eventos == ["turno.cancelado", "turno.reprogramado", "turno.confirmado", "turno.otorgado"]  # el más nuevo primero


def test_el_recordatorio_de_un_turno_tambien_llega(client, h_paciente, h_admin, autorizar, pedir_turno):
    autorizar()
    fecha = (ahora_local() + timedelta(hours=20)).replace(microsecond=0).isoformat(timespec="seconds")
    pedir_turno(fecha=fecha, confirmar=True)

    assert client.post("/api/recordatorios/ejecutar", headers=h_admin).get_json()["enviados"] == 1

    assert _avisos(client, h_paciente)[0]["evento"] == "turno.recordatorio"
    assert _textos(client, h_paciente)[0].startswith("Recordatorio: Paula tiene un turno médico el ")


def test_con_el_canal_email_el_aviso_lleva_asunto(client, h_paciente, autorizar, pedir_turno):
    autorizar(canal="email", contacto="Marta@Mail.com")
    pedir_turno()

    aviso = _avisos(client, h_paciente)[0]

    assert aviso["canal"] == "email"
    assert aviso["destino"] == "marta@mail.com"
    assert aviso["asunto"] == "Aviso de turno médico - App PAMI"
    assert aviso["texto"].startswith("Hola Marta Gómez:")


# ---------- cuando no corresponde avisar ----------

def test_sin_familiar_autorizado_no_se_envia_nada(client, h_paciente, pedir_turno):
    pedir_turno(confirmar=True)

    assert _avisos(client, h_paciente) == []


def test_si_el_paciente_quita_la_autorizacion_no_se_envia_mas(client, h_paciente, h_admin, autorizar, pedir_turno):
    autorizar()
    turno_id = pedir_turno()
    client.delete("/api/familiar", headers=h_paciente)

    client.patch(f"/api/turnos/{turno_id}/cancelar", headers=h_admin)

    # sin familiar autorizado no hay nada que mostrar ni se sigue enviando
    assert _avisos(client, h_paciente)[0]["evento"] == "turno.otorgado"
    assert len(_avisos(client, h_paciente)) == 1


def test_el_rechazo_del_turno_no_se_avisa(client, h_paciente, autorizar, pedir_turno):
    autorizar()
    turno_id = pedir_turno()

    client.patch(f"/api/turnos/{turno_id}/rechazar", headers=h_paciente)

    assert [a["evento"] for a in _avisos(client, h_paciente)] == ["turno.otorgado"]


def test_los_avisos_de_medicacion_no_llegan_al_familiar(client, app, h_paciente, h_medico, h_admin, autorizar):
    autorizar()
    receta = {"paciente_id": _id_de(client, h_paciente), "medicamentos": [{"nombre": "Ibuprofeno", "dosis": "400 mg"}]}
    receta_id = client.post("/api/recetas", json=receta, headers=h_medico).get_json()["id"]
    hace_cinco = (ahora_local() - timedelta(minutes=5)).strftime("%H:%M")
    plan = {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": [hace_cinco], "duracion_dias": 5}]}
    client.put(f"/api/recetas/{receta_id}/plan", json=plan, headers=h_medico)
    client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico)
    dos_dias = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
    app.db.recetas.update_one({"_id": ObjectId(receta_id)}, {"$set": {"inicio_plan": dos_dias}})

    assert client.post("/api/recordatorios/ejecutar", headers=h_admin).get_json()["tomas"] == 1

    # la medicación es un dato de salud: el paciente la recibe, el familiar no
    assert _avisos(client, h_paciente) == []


def test_cada_paciente_ve_solo_los_avisos_de_su_familiar(client, auth_headers, h_paciente, autorizar, pedir_turno):
    autorizar()
    pedir_turno()
    cuerpo = {"nombre": "Otro Paciente", "email": "otro@pamiapp.com", "telefono": "2615550000", "dni": "29888777", "password": "Clave12345"}
    client.post("/api/auth/registro", json=cuerpo)
    h_otro = auth_headers("otro@pamiapp.com", "Clave12345")

    assert _avisos(client, h_otro) == []


# ---------- el observer no rompe la operación ----------

def test_si_falla_el_envio_el_turno_se_otorga_igual(client, h_paciente, autorizar, pedir_turno, monkeypatch):
    autorizar()

    def roto(self, familiar, texto):
        raise RuntimeError("el proveedor de SMS no responde")

    monkeypatch.setattr(CanalSMS, "enviar", roto)

    turno_id = pedir_turno()  # otorgar responde 200 aunque el aviso al familiar falle

    turnos = client.get("/api/turnos/mios", headers=h_paciente).get_json()
    assert [t["estado"] for t in turnos if t["id"] == turno_id] == ["otorgado"]
    assert _avisos(client, h_paciente) == []


# ---------- el paciente sigue recibiendo sus propios avisos ----------

def test_el_aviso_al_familiar_no_reemplaza_el_del_paciente(client, h_paciente, autorizar, pedir_turno):
    autorizar()
    pedir_turno()

    notifs = client.get("/api/notificaciones/mias", headers=h_paciente).get_json()

    assert [n["tipo"] for n in notifs] == ["turno_otorgado"]
