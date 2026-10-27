"""Sprint 3 (JAVI123-3): avisos de toma de medicación según el plan de la receta."""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.services.recordatorio_service import ahora_local

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")


def _hace_minutos(minutos: int) -> str:
    """Hora local de hace `minutos` minutos, como "HH:MM" (lo que escribe el médico en el plan)."""
    return (ahora_local() - timedelta(minutes=minutos)).strftime("%H:%M")


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
def crear_receta(client, app, h_paciente, h_medico):
    """Devuelve una función que deja una receta del paciente con plan de medicación (emitida si se pide)."""

    def _crear(horarios, emitir=True, tipo="receta", dias=5, adelantar_inicio=True) -> str:
        cuerpo = {"tipo": tipo, "paciente_id": _id_de(client, h_paciente), "indicaciones": "Reposo"}
        if tipo == "receta":
            cuerpo["medicamentos"] = [{"nombre": "Ibuprofeno", "dosis": "400 mg"}]
        else:
            cuerpo["indicaciones"] = "Análisis de sangre completo"
        receta_id = client.post("/api/recetas", json=cuerpo, headers=h_medico).get_json()["id"]
        if tipo == "receta" and horarios:
            plan = {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": horarios, "duracion_dias": dias}]}
            assert client.put(f"/api/recetas/{receta_id}/plan", json=plan, headers=h_medico).status_code == 200
        if emitir:
            assert client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico).status_code == 200
            if adelantar_inicio:
                # el plan empieza al emitir; se lo corre dos días atrás para poder probar una toma de hace unos minutos
                hace_dos_dias = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
                app.db.recetas.update_one({"_id": ObjectId(receta_id)}, {"$set": {"inicio_plan": hace_dos_dias}})
        return receta_id

    return _crear


def _ejecutar(client, headers):
    return client.post("/api/recordatorios/ejecutar", headers=headers)


def _tomas(client, headers):
    notifs = client.get("/api/notificaciones/mias", headers=headers).get_json()
    return [n for n in notifs if n["tipo"] == "toma_medicacion"]


def test_el_paciente_recibe_el_aviso_de_su_toma(client, h_paciente, h_admin, crear_receta):
    receta_id = crear_receta([_hace_minutos(5)])

    resp = _ejecutar(client, h_admin)

    assert resp.status_code == 200
    assert resp.get_json()["tomas"] == 1
    aviso = _tomas(client, h_paciente)[0]
    assert aviso["receta_id"] == receta_id
    assert aviso["mensaje"].startswith("Es hora de tomar Ibuprofeno (400 mg)")
    assert aviso["leida"] is False
    assert "turno_id" not in aviso


def test_ejecutarlo_de_nuevo_no_repite_el_aviso(client, h_paciente, h_admin, crear_receta):
    crear_receta([_hace_minutos(5)])

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 1
    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0
    assert len(_tomas(client, h_paciente)) == 1


def test_no_avisa_una_toma_que_ya_paso_hace_mas_de_media_hora(client, h_paciente, h_admin, crear_receta):
    crear_receta([_hace_minutos(45)])

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0
    assert _tomas(client, h_paciente) == []


def test_no_avisa_una_receta_en_borrador(client, h_paciente, h_admin, crear_receta):
    crear_receta([_hace_minutos(5)], emitir=False)

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0
    assert _tomas(client, h_paciente) == []


def test_una_orden_no_genera_avisos(client, h_paciente, h_admin, crear_receta):
    crear_receta([], tipo="orden")

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0


def test_una_receta_sin_plan_no_genera_avisos(client, h_paciente, h_admin, crear_receta):
    crear_receta([])

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0


def test_el_plan_no_avisa_tomas_anteriores_a_su_inicio(client, h_paciente, h_admin, crear_receta):
    # sin adelantar el inicio, el plan empieza ahora: la toma de hace 5 minutos no corresponde
    crear_receta([_hace_minutos(5)], adelantar_inicio=False)

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0


def test_el_aviso_es_solo_del_paciente_de_la_receta(client, h_paciente, h_medico, h_admin, crear_receta):
    crear_receta([_hace_minutos(5)])
    _ejecutar(client, h_admin)

    assert _tomas(client, h_admin) == []  # el administrativo no recibe el aviso del paciente
    assert client.get("/api/notificaciones/mias", headers=h_medico).status_code == 403


def test_la_receta_emitida_muestra_cuando_empieza_el_plan(client, h_paciente, h_medico, crear_receta):
    crear_receta(["08:00"], adelantar_inicio=False)

    receta = client.get("/api/recetas/mias", headers=h_paciente).get_json()[0]
    assert datetime.fromisoformat(receta["inicio_plan"]) <= datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.parametrize("quien", ["h_paciente", "h_medico"])
def test_solo_el_administrativo_genera_los_avisos(client, request, crear_receta, quien):
    crear_receta([_hace_minutos(5)])

    assert _ejecutar(client, request.getfixturevalue(quien)).status_code == 403
    assert _tomas(client, request.getfixturevalue("h_paciente")) == []
