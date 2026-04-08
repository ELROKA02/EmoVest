from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Operacion, Cuenta_Trading
from schemas import OperacionCreate, OperacionUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/operaciones", tags=["operaciones"])

@router.get("/")
def get_operaciones(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Asumir que hay una cuenta activa, por simplicidad tomar la primera
    cuenta = db.query(Cuenta_Trading).filter(Cuenta_Trading.id_usuario == current_user["id"]).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="No hay cuenta de trading activa")
    operaciones = db.query(Operacion).filter(Operacion.id_cuenta == cuenta.id).all()
    return operaciones

@router.post("/")
def create_operacion(operacion: OperacionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cuenta = db.query(Cuenta_Trading).filter(Cuenta_Trading.id_usuario == current_user["id"]).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="No hay cuenta de trading activa")
    nueva_operacion = Operacion(
        id_cuenta=cuenta.id,
        fecha_hora=operacion.fecha_hora,
        tipo_operacion=operacion.tipo_operacion,
        cantidad=operacion.cantidad,
        activo=operacion.activo,
        precio_entrada=operacion.precio_entrada,
        precio_salida=operacion.precio_salida,
        notas=operacion.notas
    )
    db.add(nueva_operacion)
    db.commit()
    db.refresh(nueva_operacion)
    return nueva_operacion

@router.put("/{id}")
def update_operacion(id: int, operacion: OperacionUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cuenta = db.query(Cuenta_Trading).filter(Cuenta_Trading.id_usuario == current_user["id"]).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="No hay cuenta de trading activa")
    op = db.query(Operacion).filter(Operacion.id == id, Operacion.id_cuenta == cuenta.id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
    for key, value in operacion.dict(exclude_unset=True).items():
        setattr(op, key, value)
    db.commit()
    db.refresh(op)
    return op

@router.delete("/{id}")
def delete_operacion(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cuenta = db.query(Cuenta_Trading).filter(Cuenta_Trading.id_usuario == current_user["id"]).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="No hay cuenta de trading activa")
    op = db.query(Operacion).filter(Operacion.id == id, Operacion.id_cuenta == cuenta.id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
    db.delete(op)
    db.commit()
    return {"message": "Operación eliminada"}