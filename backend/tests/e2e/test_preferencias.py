URL = "/api/usuarios/me/preferencias"
PACIENTE = ("paciente@pamiapp.com", "Paciente1234")
ADMIN = ("admin@pamiapp.com", "Admin1234")
GRANDE = {"tamano_letra": "grande", "alto_contraste": True, "voz_activada": False}
POR_DEFECTO = {"tamano_letra": "normal", "alto_contraste": False, "voz_activada": True}


def test_sin_token_da_401(client):
    assert client.get(URL).status_code == 401
    assert client.put(URL, json=GRANDE).status_code == 401



def test_get_devuelve_valores_por_defecto(client, auth_headers):
    resp = client.get(URL, headers=auth_headers(*PACIENTE))
    assert resp.status_code == 200
    assert resp.get_json() == POR_DEFECTO


def test_put_guarda_y_get_lo_devuelve(client, auth_headers):
    h = auth_headers(*PACIENTE)
    resp = client.put(URL, json=GRANDE, headers=h)
    assert resp.status_code == 200
    assert resp.get_json() == GRANDE
    assert client.get(URL, headers=h).get_json() == GRANDE


def test_se_mantiene_al_volver_a_iniciar_sesion(client, auth_headers):
    client.put(URL, json=GRANDE, headers=auth_headers(*PACIENTE))
    nuevo_login = auth_headers(*PACIENTE)
    assert client.get(URL, headers=nuevo_login).get_json() == GRANDE


def test_valor_invalido_da_400(client, auth_headers):
    h = auth_headers(*PACIENTE)
    assert client.put(URL, json={**GRANDE, "tamano_letra": "enorme"}, headers=h).status_code == 400
    assert client.put(URL, json={**GRANDE, "alto_contraste": "si"}, headers=h).status_code == 400
    assert client.put(URL, json={"tamano_letra": "normal"}, headers=h).status_code == 400
    assert client.put(URL, headers=h).status_code == 400


def test_un_dato_invalido_no_pisa_lo_guardado(client, auth_headers):
    h = auth_headers(*PACIENTE)
    client.put(URL, json=GRANDE, headers=h)
    client.put(URL, json={**GRANDE, "tamano_letra": "enorme"}, headers=h)
    assert client.get(URL, headers=h).get_json() == GRANDE


def test_no_se_puede_modificar_la_cuenta_de_otro(client, auth_headers):
    h_paciente = auth_headers(*PACIENTE)
    h_admin = auth_headers(*ADMIN)

    # intentar mandar el id de otro usuario se rechaza
    resp = client.put(URL, json={**GRANDE, "usuario_id": "000000000000000000000000"}, headers=h_admin)
    assert resp.status_code == 400

    # lo que cambia el paciente no toca al administrativo
    client.put(URL, json=GRANDE, headers=h_paciente)
    assert client.get(URL, headers=h_admin).get_json() == POR_DEFECTO


def test_cualquier_rol_puede_guardar_las_suyas(client, auth_headers):
    h_admin = auth_headers(*ADMIN)
    assert client.put(URL, json=GRANDE, headers=h_admin).status_code == 200
    assert client.get(URL, headers=h_admin).get_json() == GRANDE