from app.patterns.observer import EventBus


def test_el_observer_recibe_los_datos_del_evento():
    bus = EventBus()
    recibidos = []
    bus.suscribir("turno.otorgado", recibidos.append)

    bus.publicar("turno.otorgado", {"turno_id": "t1"})

    assert recibidos == [{"turno_id": "t1"}]


def test_varios_observers_reciben_el_mismo_evento():
    bus = EventBus()
    a, b = [], []
    bus.suscribir("receta.emitida", a.append)
    bus.suscribir("receta.emitida", b.append)

    bus.publicar("receta.emitida", {"receta_id": "r1"})

    assert a == b == [{"receta_id": "r1"}]


def test_un_evento_sin_observers_no_falla():
    EventBus().publicar("turno.solicitado", {"turno_id": "t1"})


def test_un_observer_que_falla_no_corta_a_los_demas():
    bus = EventBus()
    recibidos = []

    def roto(_datos):
        raise RuntimeError("falló")

    bus.suscribir("turno.otorgado", roto)
    bus.suscribir("turno.otorgado", recibidos.append)

    bus.publicar("turno.otorgado", {"turno_id": "t1"})

    assert recibidos == [{"turno_id": "t1"}]


def test_los_observers_solo_escuchan_su_evento():
    bus = EventBus()
    recibidos = []
    bus.suscribir("turno.otorgado", recibidos.append)

    bus.publicar("turno.rechazado", {"turno_id": "t1"})

    assert recibidos == []
