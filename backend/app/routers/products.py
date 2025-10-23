# /coffeenet/backend/app/routers/products.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth, database, models

router = APIRouter(
    prefix="/products",
    tags=["Produtos"],
    # Protege todas as rotas neste router, exigindo que o usuário seja 'cozinheiro'
    dependencies=[Depends(auth.get_current_active_kitchen_user)]
)

@router.get("/", response_model=List[schemas.Product])
def read_products(db: Session = Depends(database.get_db)):
    products = crud.get_all_products(db)
    return products

@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_new_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    return crud.create_product(db=db, product=product)

@router.put("/{product_id}", response_model=schemas.Product)
def update_existing_product(product_id: int, product_update: schemas.ProductUpdate, db: Session = Depends(database.get_db)):
    db_product = crud.update_product(db=db, product_id=product_id, product_update=product_update)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_product(product_id: int, db: Session = Depends(database.get_db)):
    deleted = crud.delete_product(db=db, product_id=product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return 

@router.put("/{product_id}/promotion", response_model=schemas.Product)
def toggle_product_promotion(product_id: int, promo_update: schemas.ProductPromotionUpdate, db: Session = Depends(database.get_db)):
    db_product = crud.update_product_promotion(db=db, product_id=product_id, promo_update=promo_update)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return db_product