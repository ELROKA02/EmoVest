from schemas import createCuentaTrading, updateCuentaTrading
from database import get_db
from fastapi import Depends, HTTPException
from fastapi import APIRouter
from sqlalchemy.orm import Session
from routers.auth import get_current_user
from datetime import datetime
from models import Cuenta_Trading





router = APIRouter(tags=["cuentas"])

@router.post("/crearcuenta")
def crear_cuenta(cuenta: createCuentaTrading, usuario: str = Depends(get_current_user), db: Session = Depends(get_db)):
    nueva_cuenta = Cuenta_Trading(
        nombre_cuenta=cuenta.nombre_cuenta,
        divisa=cuenta.divisa,
        id_usuario=usuario.id,
        saldo_inicial=cuenta.saldo_inicial,
        saldo_actual=cuenta.saldo_inicial,  
        fecha_creacion=datetime.now()
    )

    db.add(nueva_cuenta)
    db.commit()
    db.refresh(nueva_cuenta)

    return {"message": "Cuenta creada exitosamente", "cuenta_id": nueva_cuenta.id}


@router.get("/vercuentas")
def ver_cuentas(usuario: str = Depends(get_current_user), db: Session = Depends(get_db)):
    cuentas = db.query(Cuenta_Trading).filter(Cuenta_Trading.id_usuario == usuario.id).all()
   
    if not cuentas:
        raise HTTPException(status_code=404, detail="No se encontraron cuentas de trading para este usuario")

    return cuentas



@router.delete("/eliminarcuenta/{cuenta_id}")
def eliminar_cuenta(cuenta_id: int, usuario: str = Depends(get_current_user), db: Session = Depends(get_db)):
    cuenta = db.query(Cuenta_Trading).filter(Cuenta_Trading.id == cuenta_id, Cuenta_Trading.id_usuario == usuario.id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    db.delete(cuenta)
    db.commit()
    return {"message": "Cuenta eliminada exitosamente"}


@router.put("/actualizarcuenta/{cuenta_id}")
def actualizar_cuenta(cuenta_id: int, cuenta: updateCuentaTrading, usuario: str = Depends(get_current_user), db: Session = Depends(get_db)):
    cuenta_db = db.query(Cuenta_Trading).filter(Cuenta_Trading.id == cuenta_id, Cuenta_Trading.id_usuario == usuario.id).first()
    if not cuenta_db:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if cuenta.nombre_cuenta:
        cuenta_db.nombre_cuenta = cuenta.nombre_cuenta
    if cuenta.saldo_actual:
        cuenta_db.saldo_actual = cuenta.saldo_actual

    db.commit()
    db.refresh(cuenta_db)
    return {"message": "Cuenta actualizada exitosamente", "cuenta": cuenta_db}