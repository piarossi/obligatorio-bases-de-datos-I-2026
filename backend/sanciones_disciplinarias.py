"""ABM de sanciones disciplinarias. Las sanciones automáticas son intocables aquí."""
from hmac import compare_digest
from secrets import token_hex

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error


def registrar_sanciones(conectar):
    bp = Blueprint("sanciones_disciplinarias", __name__, url_prefix="/sanciones")

    @bp.before_request
    def solo_administrador():
        # Se controla también en el servidor, no únicamente ocultando botones.
        if session.get("rol") != "administrador" or not session.get("correo"):
            abort(403)

    def token_csrf():
        if "sanciones_csrf" not in session:
            session["sanciones_csrf"] = token_hex(24)
        return session["sanciones_csrf"]

    def verificar_csrf():
        if not compare_digest(request.form.get("_csrf", ""), token_csrf()):
            abort(400, "Formulario no válido.")

    def cargar_opciones(cur):
        cur.execute("""SELECT id_torneo, nombre, anio, semestre
                       FROM torneo ORDER BY anio DESC, semestre DESC""")
        torneos = cur.fetchall()
        cur.execute("""SELECT j.ci, j.nombre, j.apellido, ej.id_torneo,
                              e.nombre AS equipo
                       FROM equipo_jugador_torneo ej
                       JOIN jugador j ON j.ci=ej.ci_jugador
                       JOIN equipo e ON e.id_equipo=ej.id_equipo
                       ORDER BY ej.id_torneo DESC, e.nombre, j.apellido, j.nombre""")
        jugadores = cur.fetchall()
        return torneos, jugadores

    def leer_datos():
        try:
            ci = request.form.get("ci_jugador", "").strip()
            torneo = int(request.form.get("id_torneo", ""))
            inicio = int(request.form.get("numero_fecha_inicio", ""))
            cantidad = int(request.form.get("cantidad_fechas", ""))
        except ValueError:
            raise ValueError("Seleccioná jugador, torneo y números de fecha válidos.")
        if not ci or inicio < 1 or cantidad < 1:
            raise ValueError("Elegí un jugador e indicá fechas positivas.")
        if cantidad > 30:
            raise ValueError("La duración máxima admitida es 30 fechas.")
        return ci, torneo, inicio, cantidad

    def validar_sancion(cur, ci, torneo, inicio, cantidad, excluir=None):
        # El jugador debe integrar un plantel de esta edición.
        cur.execute("""SELECT 1 FROM equipo_jugador_torneo
                       WHERE ci_jugador=%s AND id_torneo=%s LIMIT 1""", (ci, torneo))
        if cur.fetchone() is None:
            raise ValueError("Ese jugador no integra un plantel en la edición seleccionada.")

        # No aplicar retroactivamente una sanción a fechas en las que ya aparece
        # en una planilla (esté el partido programado o jugado).
        cur.execute("""SELECT p.id_partido, p.numero_fecha
                       FROM planilla_partido pp
                       JOIN partido p ON p.id_partido=pp.id_partido
                       WHERE pp.ci_jugador=%s AND p.id_torneo=%s
                         AND p.numero_fecha >= %s
                         AND p.numero_fecha < %s
                       LIMIT 1""",
                    (ci, torneo, inicio, inicio + cantidad))
        conflicto = cur.fetchone()
        if conflicto:
            raise ValueError(
                f"El jugador ya figura en la planilla del partido "
                f"{conflicto['id_partido']} (fecha {conflicto['numero_fecha']})."
            )

        # No superponer sanciones disciplinarias del mismo jugador.
        cur.execute("""SELECT id_sancion FROM sancion_jugador
                       WHERE ci_jugador=%s AND id_torneo=%s
                         AND motivo='disciplinaria'
                         AND numero_fecha_inicio < %s
                         AND numero_fecha_inicio + cantidad_fechas > %s
                         AND (%s IS NULL OR id_sancion <> %s)
                       LIMIT 1""",
                    (ci, torneo, inicio + cantidad, inicio, excluir, excluir))
        if cur.fetchone():
            raise ValueError("Ya existe una sanción disciplinaria que abarca esas fechas.")

    @bp.route("/", methods=["GET", "POST"])
    def lista():
        if request.method == "POST":
            verificar_csrf()
            cn = conectar()
            try:
                cur = cn.cursor(dictionary=True, buffered=True)
                try:
                    try:
                        ci, torneo, inicio, cantidad = leer_datos()
                        # Serializa con operaciones de planillas/eventos que bloquean torneo.
                        cur.execute("SELECT id_torneo FROM torneo WHERE id_torneo=%s FOR UPDATE", (torneo,))
                        if cur.fetchone() is None:
                            raise ValueError("La edición no existe.")
                        validar_sancion(cur, ci, torneo, inicio, cantidad)
                        cur.execute("""INSERT INTO sancion_jugador
                                       (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas)
                                       VALUES (%s,%s,'disciplinaria',%s,%s)""",
                                    (ci, torneo, inicio, cantidad))
                        cn.commit()
                        flash("Sanción disciplinaria registrada correctamente.")
                        return redirect(url_for(".lista"))
                    except ValueError as exc:
                        cn.rollback()
                        flash(str(exc))
                    except Error:
                        cn.rollback()
                        flash("No se pudo registrar la sanción. Revisá los datos.")
                finally:
                    cur.close()
            finally:
                cn.close()

        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                cur.execute("""SELECT s.id_sancion, s.ci_jugador, s.id_torneo, s.motivo,
                                      s.numero_fecha_inicio, s.cantidad_fechas,
                                      j.nombre, j.apellido, t.nombre AS torneo
                               FROM sancion_jugador s
                               JOIN jugador j ON j.ci=s.ci_jugador
                               JOIN torneo t ON t.id_torneo=s.id_torneo
                               ORDER BY s.id_torneo DESC, s.numero_fecha_inicio,
                                        j.apellido, s.id_sancion""")
                sanciones = cur.fetchall()
                torneos, jugadores = cargar_opciones(cur)
            finally:
                cur.close()
        finally:
            cn.close()
        return render_template("sanciones_disciplinarias.html",
                               sanciones=sanciones, torneos=torneos,
                               jugadores=jugadores, csrf=token_csrf())

    @bp.route("/<int:id_sancion>/editar", methods=["GET", "POST"])
    def editar(id_sancion):
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                cur.execute("""SELECT * FROM sancion_jugador
                               WHERE id_sancion=%s AND motivo='disciplinaria'""",
                            (id_sancion,))
                sancion = cur.fetchone()
                if sancion is None:
                    abort(404)

                if request.method == "POST":
                    verificar_csrf()
                    try:
                        ci, torneo, inicio, cantidad = leer_datos()
                        cur.execute("SELECT id_torneo FROM torneo WHERE id_torneo=%s FOR UPDATE", (torneo,))
                        if cur.fetchone() is None:
                            raise ValueError("La edición no existe.")
                        # Sólo editamos la sanción disciplinaria que se abrió.
                        cur.execute("""SELECT id_sancion FROM sancion_jugador
                                       WHERE id_sancion=%s AND motivo='disciplinaria'
                                       FOR UPDATE""", (id_sancion,))
                        if cur.fetchone() is None:
                            abort(404)
                        validar_sancion(cur, ci, torneo, inicio, cantidad, id_sancion)
                        cur.execute("""UPDATE sancion_jugador
                                       SET ci_jugador=%s, id_torneo=%s,
                                           numero_fecha_inicio=%s, cantidad_fechas=%s
                                       WHERE id_sancion=%s AND motivo='disciplinaria'""",
                                    (ci, torneo, inicio, cantidad, id_sancion))
                        cn.commit()
                        flash("Sanción actualizada.")
                        return redirect(url_for(".lista"))
                    except ValueError as exc:
                        cn.rollback()
                        flash(str(exc))
                    except Error:
                        cn.rollback()
                        flash("No se pudo modificar la sanción.")

                torneos, jugadores = cargar_opciones(cur)
            finally:
                cur.close()
        finally:
            cn.close()
        return render_template("sancion_editar.html", sancion=sancion,
                               torneos=torneos, jugadores=jugadores, csrf=token_csrf())

    @bp.post("/<int:id_sancion>/eliminar")
    def eliminar(id_sancion):
        verificar_csrf()
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                try:
                    cur.execute("""SELECT id_torneo FROM sancion_jugador
                                   WHERE id_sancion=%s AND motivo='disciplinaria'""",
                                (id_sancion,))
                    sancion = cur.fetchone()
                    if sancion is None:
                        abort(404)
                    cur.execute("SELECT id_torneo FROM torneo WHERE id_torneo=%s FOR UPDATE",
                                (sancion["id_torneo"],))
                    cur.fetchone()
                    cur.execute("""DELETE FROM sancion_jugador
                                   WHERE id_sancion=%s AND motivo='disciplinaria'""",
                                (id_sancion,))
                    cn.commit()
                    flash("Sanción disciplinaria eliminada.")
                except Error:
                    cn.rollback()
                    flash("No se pudo eliminar la sanción.")
            finally:
                cur.close()
        finally:
            cn.close()
        return redirect(url_for(".lista"))

    return bp
