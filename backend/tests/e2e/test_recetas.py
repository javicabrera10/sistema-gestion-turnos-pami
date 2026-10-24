import pytest

from app.security.passwords import hash_password

PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
MEDICO = ("medico@pamiapp.com", "Medico1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")
OTRO_MEDICO = ("otro.medico@pamiapp.com", "OtroMedico1234")

IBUPROFENO = {"nombre": "Ibuprofeno", "dosis": "400 mg", "horario_toma": "Cada 8 horas"}
PLAN = {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": ["08:00", "16:00"], "duracion_dias": 7}]}


@pytest.fixture
def h_medico(auth_headers):
    return auth_headers(*MEDICO)


@pytest.fixture
def h_paciente(auth_headers):
    return auth_headers(*PACIENTE)


@pytest.fixture
def h_otro_medico(app, auth_headers):
    app.db.usuarios.insert_one(
        {
            "nombre": "Otra Médica", "email": OTRO_MEDICO[0], "telefono": "2610000099", "rol": "medico",
            "especialidad": "Cardiología", "password_hash": hash_password(OTRO_MEDICO[1]),
            "intentos_fallidos": 0, "bloqueado_hasta": None,
        }
    )
    return auth_headers(*OTRO_MEDICO)


@pytest.fixture
def paciente_id(client, h_paciente):
    return client.get("/api/auth/me", headers=h_paciente).get_json()["id"]


def _crear_receta(client, headers, paciente_id, **extra):
    cuerpo = {"paciente_id": paciente_id, "medicamentos": [IBUPROFENO], **extra}
    return client.post("/api/recetas", json=cuerpo, headers=headers)


# ---------- crear ----------

def test_medico_crea_una_receta_y_queda_en_borrador(client, h_medico, paciente_id):
    resp = _crear_receta(client, h_medico, paciente_id)

    assert resp.status_code == 201
    receta = resp.get_json()
    assert receta["estado"] == "borrador"
    assert receta["tipo"] == "receta"
    assert receta["paciente_id"] == paciente_id
    assert receta["medicamentos"][0]["nombre"] == "Ibuprofeno"
    assert receta["id"]


def test_la_ruta_funciona_con_y_sin_barra_final(client, h_medico, paciente_id):
    # Con un 308 el navegador bloquea el pedido por CORS: tiene que responder directo
    assert _crear_receta(client, h_medico, paciente_id).status_code == 201
    assert client.post(
        "/api/recetas/", json={"paciente_id": paciente_id, "medicamentos": [IBUPROFENO]}, headers=h_medico
    ).status_code == 201
    assert client.get("/api/recetas", headers=h_medico).status_code == 200
    assert client.get("/api/recetas/", headers=h_medico).status_code == 200


def test_medico_crea_una_orden_con_su_contenido(client, h_medico, paciente_id):
    resp = client.post(
        "/api/recetas",
        json={"tipo": "orden", "paciente_id": paciente_id, "indicaciones": "Radiografía de rodilla izquierda"},
        headers=h_medico,
    )

    assert resp.status_code == 201
    assert resp.get_json()["tipo"] == "orden"
    assert resp.get_json()["indicaciones"] == "Radiografía de rodilla izquierda"


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"medicamentos": []},                                   # receta sin medicamentos
        {},                                                     # falta el campo medicamentos
        {"medicamentos": [IBUPROFENO], "medico_id": "b" * 24},  # el cliente no manda el médico
        {"medicamentos": [IBUPROFENO], "estado": "emitida"},    # ni el estado
        {"tipo": "orden"},                                      # orden sin indicaciones
    ],
)
def test_datos_invalidos_devuelven_400(client, h_medico, paciente_id, cuerpo):
    resp = client.post("/api/recetas", json={"paciente_id": paciente_id, **cuerpo}, headers=h_medico)

    assert resp.status_code == 400


def test_el_paciente_debe_existir(client, h_medico):
    assert _crear_receta(client, h_medico, "f" * 24).status_code == 400


@pytest.mark.parametrize("rol", [PACIENTE, ADMIN])
def test_solo_el_medico_crea_recetas(client, auth_headers, paciente_id, rol):
    assert _crear_receta(client, auth_headers(*rol), paciente_id).status_code == 403


def test_sin_token_devuelve_401(client):
    assert client.post("/api/recetas", json={}).status_code == 401


# ---------- emitir ----------

def test_medico_emite_y_el_paciente_la_ve(client, h_medico, h_paciente, paciente_id):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]
    assert client.get("/api/recetas/mias", headers=h_paciente).get_json() == []  # borrador: no la ve

    resp = client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico)

    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "emitida"
    mias = client.get("/api/recetas/mias", headers=h_paciente).get_json()
    assert [r["id"] for r in mias] == [receta_id]


def test_no_se_emite_dos_veces(client, h_medico, paciente_id):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]
    client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico)

    assert client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico).status_code == 409


def test_el_paciente_no_puede_emitir_ni_usar_las_rutas_del_medico(client, h_medico, h_paciente, paciente_id):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]

    assert client.post(f"/api/recetas/{receta_id}/emitir", headers=h_paciente).status_code == 403
    assert client.get("/api/recetas", headers=h_paciente).status_code == 403
    assert client.put(f"/api/recetas/{receta_id}", json={"indicaciones": "abc"}, headers=h_paciente).status_code == 403
    assert client.delete(f"/api/recetas/{receta_id}", headers=h_paciente).status_code == 403
    assert client.put(f"/api/recetas/{receta_id}/plan", json=PLAN, headers=h_paciente).status_code == 403


def test_el_medico_no_usa_la_ruta_del_paciente(client, h_medico):
    assert client.get("/api/recetas/mias", headers=h_medico).status_code == 403


# ---------- recetas de otro médico ----------

def test_un_medico_no_toca_las_recetas_de_otro(client, h_medico, h_otro_medico, paciente_id):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]

    assert client.put(f"/api/recetas/{receta_id}", json={"indicaciones": "ajeno"}, headers=h_otro_medico).status_code == 404
    assert client.delete(f"/api/recetas/{receta_id}", headers=h_otro_medico).status_code == 404
    assert client.post(f"/api/recetas/{receta_id}/emitir", headers=h_otro_medico).status_code == 404
    assert client.put(f"/api/recetas/{receta_id}/plan", json=PLAN, headers=h_otro_medico).status_code == 404
    assert client.get("/api/recetas", headers=h_otro_medico).get_json() == []
    # la receta sigue intacta para su autor
    assert len(client.get("/api/recetas", headers=h_medico).get_json()) == 1


# ---------- editar, eliminar y plan ----------

def test_editar_una_receta_emitida(client, h_medico, paciente_id):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]
    client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico)

    resp = client.put(f"/api/recetas/{receta_id}", json={"indicaciones": "Tomar con las comidas"}, headers=h_medico)

    assert resp.status_code == 200
    assert resp.get_json()["indicaciones"] == "Tomar con las comidas"
    assert resp.get_json()["estado"] == "emitida"


@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"medicamentos": []}, {"paciente_id": "a" * 24}, {"tipo": "orden"}],
)
def test_edicion_invalida_devuelve_400(client, h_medico, paciente_id, cuerpo):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]

    assert client.put(f"/api/recetas/{receta_id}", json=cuerpo, headers=h_medico).status_code == 400


def test_eliminar_una_receta_emitida_la_saca_de_la_vista_del_paciente(client, h_medico, h_paciente, paciente_id):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]
    client.post(f"/api/recetas/{receta_id}/emitir", headers=h_medico)

    assert client.delete(f"/api/recetas/{receta_id}", headers=h_medico).status_code == 200

    assert client.get("/api/recetas/mias", headers=h_paciente).get_json() == []
    assert client.delete(f"/api/recetas/{receta_id}", headers=h_medico).status_code == 404


def test_registrar_el_plan_de_medicacion(client, h_medico, paciente_id):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]

    resp = client.put(f"/api/recetas/{receta_id}/plan", json=PLAN, headers=h_medico)

    assert resp.status_code == 200
    item = resp.get_json()["plan_medicacion"][0]
    assert item["medicamento"] == "Ibuprofeno"
    assert item["horarios"] == ["08:00", "16:00"]
    assert item["duracion_dias"] == 7


@pytest.mark.parametrize(
    "plan",
    [
        {"plan": []},
        {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": ["25:00"], "duracion_dias": 7}]},
        {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": ["08:00"], "duracion_dias": 0}]},
    ],
)
def test_plan_invalido_devuelve_400(client, h_medico, paciente_id, plan):
    receta_id = _crear_receta(client, h_medico, paciente_id).get_json()["id"]

    assert client.put(f"/api/recetas/{receta_id}/plan", json=plan, headers=h_medico).status_code == 400


def test_una_orden_no_lleva_plan(client, h_medico, paciente_id):
    orden_id = client.post(
        "/api/recetas",
        json={"tipo": "orden", "paciente_id": paciente_id, "indicaciones": "Análisis de sangre"},
        headers=h_medico,
    ).get_json()["id"]

    assert client.put(f"/api/recetas/{orden_id}/plan", json=PLAN, headers=h_medico).status_code == 409


def test_un_id_malformado_devuelve_404(client, h_medico):
    assert client.post("/api/recetas/no-es-un-id/emitir", headers=h_medico).status_code == 404


def test_swagger_documenta_los_endpoints_de_recetas(client):
    spec = client.get("/apispec_1.json").get_json()
    for ruta in (
        "/api/recetas", "/api/recetas/mias", "/api/recetas/{receta_id}",
        "/api/recetas/{receta_id}/emitir", "/api/recetas/{receta_id}/plan",
    ):
        assert ruta in spec["paths"]
