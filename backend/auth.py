
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import check_password_hash


def registrar_auth(conectar):
    bp = Blueprint("auth", __name__)

    @bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            correo = request.form.get("correo", "").strip().lower()
            contrasena = request.form.get("contrasena", "")

            cn = conectar()
            try:
                cursor = cn.cursor(dictionary=True)
                try:
                    cursor.execute(
                        """
                        SELECT correo, contrasena, rol
                        FROM login
                        WHERE correo = %s
                        """,
                        (correo,)
                    )
                    usuario = cursor.fetchone()
                finally:
                    cursor.close()
            finally:
                cn.close()

            if usuario and check_password_hash(
                usuario["contrasena"], contrasena
            ):
                session.clear()
                session["correo"] = usuario["correo"]
                session["rol"] = usuario["rol"]
                return redirect(url_for("listar_equipos"))

            flash("Correo o contraseña incorrectos.")

        return render_template("login.html")

    @bp.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("auth.login"))

    return bp
