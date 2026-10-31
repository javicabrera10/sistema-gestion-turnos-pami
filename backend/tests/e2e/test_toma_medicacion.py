"""Sprint 3 (JAVI123-3): el médico emite la receta, el administrativo se entera y genera el recordatorio para el paciente."""

from datetime import datetime, timezone

import pytest

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")

PLAN = {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": ["08:00", "20:00"], "duracion_dias": 5}]}


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
def crear_receta(client, h_paciente, h_medico):
    """Devuelve una función que deja una receta del paciente, con plan de medicación y emitida si se pide."""

    def _crear(con_plan=True, emitir=True, tipo="receta") -> str:
        cuerpo = {"tipo": tipo, "paciente_id": _id_de(client, h_paciente), "indicaciones": "Después de las comidas"}
        if tipo == "receta":
            cuerpo["medicamentos"] = [{"nombre": "Ibuprofeno", "dosis": "400 mg"}]
        else:
            cuerpo["indicaciones"] = "Análisis de sangre completo"
        receta_id = client.post("/api/recetas", json=cuerpo, headers=h_medico).get_json()["id"]
        if tipo == "receta" and con_plan:
            assert client.put(f"/api/recetas/{receta_id}/plan", json=PLAN, headers=h_medico).status_code == 200
        if emitir:
            assert client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico).status_code == 200
        return receta_id

    return _crear


def _ejecutar(client, headers):
    return client.post("/api/recordatorios/ejecutar", headers=headers)


def _avisos(client, headers, tipo):
    notifs = client.get("/api/notificaciones/mias", headers=headers).get_json()
    return [n for n in notifs if n["tipo"] == tipo]


# ---------- al emitir: le llega al administrativo, el paciente todavía no recibe nada ----------

def test_al_emitir_el_administrativo_recibe_el_aviso_y_el_paciente_todavia_no(client, h_paciente, h_admin, crear_receta):
    receta_id = crear_receta()

    aviso = _avisos(client, h_admin, "receta_emitida")[0]
    assert aviso["receta_id"] == receta_id
    assert aviso["leida"] is False
    assert aviso["mensaje"].startswith("Martín Médico emitió una receta con plan de medicación para Paula Paciente.")
    assert "Generar recordatorios" in aviso["mensaje"]
    assert client.get("/api/notificaciones/mias", headers=h_paciente).get_json() == []


def test_el_aviso_al_administrativo_no_lleva_medicamentos_ni_dosis(client, h_admin, crear_receta):
    crear_receta()

    mensaje = _avisos(client, h_admin, "receta_emitida")[0]["mensaje"]
    assert "Ibuprofeno" not in mensaje
    assert "400 mg" not in mensaje


@pytest.mark.parametrize("caso", [{"con_plan": False}, {"tipo": "orden"}])
def test_una_receta_sin_plan_o_una_orden_no_avisan_al_administrativo(client, h_admin, crear_receta, caso):
    crear_receta(**caso)

    assert _avisos(client, h_admin, "receta_emitida") == []


def test_un_borrador_no_avisa_hasta_que_se_emite(client, h_admin, h_medico, crear_receta):
    receta_id = crear_receta(emitir=False)
    assert _avisos(client, h_admin, "receta_emitida") == []

    client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico)

    assert len(_avisos(client, h_admin, "receta_emitida")) == 1


def test_si_hay_varios_administrativos_a_todos_les_llega(app, client, h_admin, crear_receta):
    segundo = {"nombre": "Alba Administrativa", "email": "alba@pamiapp.com", "rol": "administrativo", "password_hash": "x"}
    segundo_id = str(app.db.usuarios.insert_one(segundo).inserted_id)

    crear_receta()

    assert len(_avisos(client, h_admin, "receta_emitida")) == 1
    assert app.db.notificaciones.count_documents({"destinatario_id": segundo_id, "tipo": "receta_emitida"}) == 1


# ---------- al tocar el botón: el paciente recibe la receta y el plan de toma ----------

def test_al_tocar_el_boton_el_paciente_recibe_la_receta_y_el_plan_de_toma(client, h_paciente, h_admin, crear_receta):
    receta_id = crear_receta()

    resp = _ejecutar(client, h_admin)

    assert resp.status_code == 200
    assert resp.get_json()["tomas"] == 1
    aviso = _avisos(client, h_paciente, "toma_medicacion")[0]
    assert aviso["receta_id"] == receta_id
    assert aviso["leida"] is False
    assert "turno_id" not in aviso
    assert "Ibuprofeno (400 mg) a las 08:00, 20:00 hs durante 5 días" in aviso["mensaje"]
    assert "Indicaciones: Después de las comidas" in aviso["mensaje"]


def test_el_aviso_sale_al_tocar_el_boton_y_no_a_la_hora_de_cada_toma(client, h_paciente, h_admin, crear_receta):
    crear_receta()
    assert _avisos(client, h_paciente, "toma_medicacion") == []  # emitida pero sin tocar el botón

    _ejecutar(client, h_admin)

    assert len(_avisos(client, h_paciente, "toma_medicacion")) == 1  # uno solo, aunque la receta tenga dos horarios


def test_tocar_el_boton_de_nuevo_no_repite_el_aviso(client, h_paciente, h_admin, crear_receta):
    crear_receta()

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 1
    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0
    assert len(_avisos(client, h_paciente, "toma_medicacion")) == 1


def test_al_tocar_el_boton_se_marca_como_leido_el_aviso_pendiente_del_administrativo(client, h_admin, crear_receta):
    crear_receta()
    assert _avisos(client, h_admin, "receta_emitida")[0]["leida"] is False

    _ejecutar(client, h_admin)

    assert _avisos(client, h_admin, "receta_emitida")[0]["leida"] is True


def test_no_entrega_una_receta_en_borrador(client, h_paciente, h_admin, crear_receta):
    crear_receta(emitir=False)

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0
    assert _avisos(client, h_paciente, "toma_medicacion") == []


def test_una_orden_o_una_receta_sin_plan_no_generan_aviso(client, h_paciente, h_admin, crear_receta):
    crear_receta(tipo="orden")
    crear_receta(con_plan=False)

    assert _ejecutar(client, h_admin).get_json()["tomas"] == 0
    assert _avisos(client, h_paciente, "toma_medicacion") == []


def test_el_aviso_es_solo_del_paciente_de_la_receta(client, h_medico, h_admin, crear_receta):
    crear_receta()
    _ejecutar(client, h_admin)

    assert _avisos(client, h_admin, "toma_medicacion") == []  # el administrativo no recibe el aviso del paciente
    assert client.get("/api/notificaciones/mias", headers=h_medico).status_code == 403


def test_el_paciente_no_ve_la_receta_con_plan_hasta_que_el_administrativo_toca_el_boton(client, h_paciente, h_admin, crear_receta):
    receta_id = crear_receta()
    assert client.get("/api/recetas/mias", headers=h_paciente).get_json() == []

    _ejecutar(client, h_admin)

    assert [r["id"] for r in client.get("/api/recetas/mias", headers=h_paciente).get_json()] == [receta_id]


def test_una_orden_o_una_receta_sin_plan_se_ven_al_emitirse(client, h_paciente, crear_receta):
    sin_plan = crear_receta(con_plan=False)
    orden = crear_receta(tipo="orden")

    vistas = {r["id"] for r in client.get("/api/recetas/mias", headers=h_paciente).get_json()}

    assert vistas == {sin_plan, orden}


def test_la_receta_muestra_cuando_se_genero_el_recordatorio(client, h_paciente, h_admin, crear_receta):
    crear_receta()
    _ejecutar(client, h_admin)

    receta = client.get("/api/recetas/mias", headers=h_paciente).get_json()[0]
    assert datetime.fromisoformat(receta["recordatorio_generado_en"]) <= datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- «Turnos y recetas»: lo que emitieron los médicos, con los datos del paciente ----------

def test_el_administrativo_ve_las_recetas_emitidas_con_los_datos_del_paciente(client, h_admin, crear_receta):
    receta_id = crear_receta()

    recetas = client.get("/api/recetas/emitidas", headers=h_admin).get_json()

    assert [r["id"] for r in recetas] == [receta_id]
    receta = recetas[0]
    assert receta["tipo"] == "receta"
    assert receta["con_plan"] is True
    assert receta["recordatorio_generado_en"] is None
    assert receta["paciente"]["nombre"] == "Paula Paciente"
    assert set(receta["paciente"]) == {"id", "nombre", "dni", "telefono"}
    assert receta["medico"]["nombre"] == "Martín Médico"


def test_las_recetas_emitidas_no_llevan_medicamentos_ni_indicaciones(client, h_admin, crear_receta):
    crear_receta()

    receta = client.get("/api/recetas/emitidas", headers=h_admin).get_json()[0]

    assert not {"medicamentos", "plan_medicacion", "indicaciones"} & set(receta)
    assert "Ibuprofeno" not in str(receta)


def test_las_recetas_emitidas_incluyen_ordenes_y_excluyen_borradores(client, h_admin, crear_receta):
    sin_plan = crear_receta(con_plan=False)
    orden = crear_receta(tipo="orden")
    crear_receta(emitir=False)

    recetas = client.get("/api/recetas/emitidas", headers=h_admin).get_json()

    assert {r["id"] for r in recetas} == {sin_plan, orden}
    assert {r["con_plan"] for r in recetas} == {False}


def test_la_receta_emitida_muestra_cuando_se_genero_el_recordatorio(client, h_admin, crear_receta):
    crear_receta()
    _ejecutar(client, h_admin)

    receta = client.get("/api/recetas/emitidas", headers=h_admin).get_json()[0]

    assert receta["recordatorio_generado_en"] is not None


@pytest.mark.parametrize("quien", ["h_paciente", "h_medico"])
def test_solo_el_administrativo_ve_las_recetas_emitidas(client, request, quien):
    assert client.get("/api/recetas/emitidas", headers=request.getfixturevalue(quien)).status_code == 403
    assert client.get("/api/recetas/emitidas").status_code == 401


@pytest.mark.parametrize("quien", ["h_paciente", "h_medico"])
def test_solo_el_administrativo_genera_los_avisos(client, request, crear_receta, quien):
    crear_receta()

    assert _ejecutar(client, request.getfixturevalue(quien)).status_code == 403
    assert _avisos(client, request.getfixturevalue("h_paciente"), "toma_medicacion") == []
