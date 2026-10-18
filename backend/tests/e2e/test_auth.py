NUEVO = {
    "nombre": "Juan Pérez", "email": "juan@pamiapp.com", "telefono": "2611234567",
    "dni": "12345678", "password": "Clave12345",
}


def test_registro_ok(client):
    resp = client.post("/api/auth/registro", json=NUEVO)
    assert resp.status_code == 201


def test_registro_email_duplicado(client):
    client.post("/api/auth/registro", json=NUEVO)
    resp = client.post("/api/auth/registro", json=NUEVO)
    assert resp.status_code == 409


def test_registro_no_permite_elegir_rol(client):
    resp = client.post("/api/auth/registro", json={**NUEVO, "rol": "administrativo"})
    assert resp.status_code == 400


def test_login_ok_devuelve_token_y_rol(login):
    resp = login("paciente@pamiapp.com", "Paciente1234")
    assert resp.status_code == 200
    assert resp.get_json()["rol"] == "paciente"
    assert resp.get_json()["access_token"]


def test_login_password_incorrecta(login):
    assert login("paciente@pamiapp.com", "mala").status_code == 401


def test_me_sin_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_rol_permitido_y_denegado(client, auth_headers):
    h_admin = auth_headers("admin@pamiapp.com", "Admin1234")
    h_paciente = auth_headers("paciente@pamiapp.com", "Paciente1234")

    ok = client.get("/api/usuarios", headers=h_admin)
    assert ok.status_code == 200
    assert "password_hash" not in ok.get_json()[0]

    assert client.get("/api/usuarios", headers=h_paciente).status_code == 403
    assert client.get("/api/usuarios").status_code == 401


def test_rate_limit_en_login(login):
    codigos = [login("nadie@pamiapp.com", "x1234567").status_code for _ in range(11)]
    assert codigos[:10] == [401] * 10
    assert codigos[10] == 429


def test_bloqueo_tras_cinco_intentos_fallidos(login):
    for _ in range(5):
        assert login("paciente@pamiapp.com", "mala-clave").status_code == 401
    # aun con la clave correcta, la cuenta queda bloqueada
    assert login("paciente@pamiapp.com", "Paciente1234").status_code == 423
