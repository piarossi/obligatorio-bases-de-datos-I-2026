"""Sanciones por tarjetas de una edición, dentro de la transacción del partido.

Una expulsión por segunda amarilla conserva dos amarillas acumulables y
una roja derivada (origen='doble_amarilla'). Si se alcanza el límite de tres
amarillas Y hay expulsión, se aplica una única suspensión. El contador se
reinicia después de cumplir la fecha de sanción; el historial se conserva.
"""
from collections import defaultdict


def recalcular_sanciones(cur, id_torneo):
    cur.execute('''
        SELECT t.ci_jugador, t.color, t.origen, p.numero_fecha,
               p.id_partido, t.id_tarjeta
        FROM tarjeta t
        JOIN partido p ON p.id_partido = t.id_partido
        WHERE p.id_torneo = %s AND p.estado IN ('programado', 'jugado')
        ORDER BY t.ci_jugador, p.numero_fecha, p.dia, p.id_partido, t.minuto, t.id_tarjeta
    ''', (id_torneo,))
    por_jugador_fecha = defaultdict(lambda: defaultdict(list))
    for tarjeta in cur.fetchall():
        por_jugador_fecha[tarjeta['ci_jugador']][tarjeta['numero_fecha']].append(tarjeta)

    nuevas = []
    for ci, fechas in por_jugador_fecha.items():
        acumuladas = 0
        fecha_suspendida = None
        for fecha in sorted(fechas):
            if fecha_suspendida is not None:
                if fecha == fecha_suspendida:
                    raise ValueError(
                        f'El jugador {ci} tiene tarjetas en su fecha de suspensión ({fecha}).'
                    )
                if fecha > fecha_suspendida:
                    acumuladas = 0
                    fecha_suspendida = None

            eventos = fechas[fecha]
            por_partido = defaultdict(list)
            for evento in eventos:
                por_partido[evento['id_partido']].append(evento)
            hay_roja = False
            amarillas_de_fecha = 0
            for grupo in por_partido.values():
                amarillas = [t for t in grupo if t['color'] == 'amarilla']
                rojas = [t for t in grupo if t['color'] == 'roja']
                if len(amarillas) > 2 or len(rojas) > 1:
                    raise ValueError(f'Hay tarjetas incompatibles para {ci} en fecha {fecha}.')
                if len(amarillas) == 2:
                    if len(rojas) != 1 or rojas[0]['origen'] != 'doble_amarilla':
                        raise ValueError('La segunda amarilla debe producir una roja por doble amonestación.')
                elif any(r['origen'] == 'doble_amarilla' for r in rojas):
                    raise ValueError('Existe roja por doble amarilla sin las dos amarillas correspondientes.')
                # Las dos amarillas de una expulsión SÍ cuentan como dos.
                # La roja derivada identifica la expulsión, sin contar como
                # una segunda sanción ni como una roja directa adicional.
                amarillas_de_fecha += len(amarillas)
                if rojas:
                    hay_roja = True

            acumuladas += amarillas_de_fecha

            # Puede coincidir la tercera amarilla con una expulsión.
            # En ese caso se genera UNA sola fecha de suspensión.
            if hay_roja or acumuladas >= 3:
                motivo = 'roja' if hay_roja else 'acumulación de amarillas'
                nuevas.append((ci, id_torneo, motivo, fecha + 1, 1))
                fecha_suspendida = fecha + 1

    # No crear sanciones que invaliden planillas futuras ya registradas.
    for ci, _, _, inicio, duracion in nuevas:
        cur.execute('''
            SELECT p.id_partido FROM planilla_partido pp
            JOIN partido p ON p.id_partido = pp.id_partido
            WHERE pp.ci_jugador = %s AND p.id_torneo = %s
              AND p.numero_fecha >= %s AND p.numero_fecha < %s
            LIMIT 1
        ''', (ci, id_torneo, inicio, inicio + duracion))
        if cur.fetchone():
            raise ValueError(
                f'No se puede sancionar a {ci}: ya figura en la planilla de fecha {inicio}.'
            )

    cur.execute('''
        DELETE FROM sancion_jugador
        WHERE id_torneo = %s AND motivo IN ('roja', 'acumulación de amarillas')
    ''', (id_torneo,))
    if nuevas:
        cur.executemany('''
            INSERT INTO sancion_jugador
              (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas)
            VALUES (%s,%s,%s,%s,%s)
        ''', nuevas)
    return len(nuevas)
