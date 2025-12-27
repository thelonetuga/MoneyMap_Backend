from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import date, timedelta
import yfinance as yf
import time  # <--- Importante para controlar o tempo
import models.models as models
import schemas.schemas as schemas
from dependencies import get_db, get_current_user

router = APIRouter(tags=["portfolio"])

# --- SISTEMA DE CACHE (Memória Temporária) ---
# Estrutura: { "AAPL": { "price": 150.0, "timestamp": 1234567890 } }
PRICE_CACHE = {}
CACHE_DURATION = 15 * 60  # 15 minutos em segundos

def get_cached_price(symbol: str):
    """Verifica se temos um preço recente guardado"""
    now = time.time()
    if symbol in PRICE_CACHE:
        data = PRICE_CACHE[symbol]
        # Se a informação tem menos de 15 minutos, é válida
        if now - data["timestamp"] < CACHE_DURATION:
            return data["price"]
    return None

def update_cache(symbol: str, price: float):
    """Guarda o preço novo na memória"""
    PRICE_CACHE[symbol] = {
        "price": price,
        "timestamp": time.time()
    }

@router.get("/portfolio", response_model=schemas.PortfolioResponse) 
def get_portfolio(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    account_ids = [acc.id for acc in accounts]
    
    total_cash = sum(acc.current_balance for acc in accounts)
    
    # Busca todas as posições em todas as contas
    holdings = db.query(models.Holding).options(joinedload(models.Holding.asset)).filter(models.Holding.account_id.in_(account_ids)).filter(models.Holding.quantity > 0).all()
    
    # --- LÓGICA DE PREÇOS (YAHOO) ---
    symbols_needed = set([h.asset.symbol for h in holdings]) # 'set' remove duplicados na lista de pesquisa
    symbols_to_fetch = []
    
    current_prices = {}
    for sym in symbols_needed:
        cached = get_cached_price(sym)
        if cached:
            current_prices[sym] = cached
        else:
            symbols_to_fetch.append(sym)

    if symbols_to_fetch:
        try:
            tickers = yf.Tickers(' '.join(symbols_to_fetch))
            for symbol in symbols_to_fetch:
                try:
                    # Verifica se o ticker existe na resposta
                    if symbol in tickers.tickers:
                        info = tickers.tickers[symbol].info
                        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                        
                        if price:
                            current_prices[symbol] = price
                            update_cache(symbol, price)
                except Exception:
                    print(f"Erro ao buscar ticker individual: {symbol}")
        except Exception as e:
            print(f"Erro geral Yahoo: {e}")

    # --- CALCULAR E CONSOLIDAR (A CORREÇÃO ESTÁ AQUI) ---
    
    # 1. Dicionário para agrupar por Símbolo
    portfolio_map = {} 

    for h in holdings:
        symbol = h.asset.symbol
        
        # Determinar preço atual
        real_time_price = current_prices.get(symbol)
        curr_price = real_time_price if real_time_price else h.avg_buy_price

        if symbol not in portfolio_map:
            portfolio_map[symbol] = {
                "quantity": 0.0,
                "total_cost": 0.0,      # Custo total de aquisição (para calcular média depois)
                "current_price": curr_price,
                "symbol": symbol
            }
        
        # Acumular valores (Agregação)
        portfolio_map[symbol]["quantity"] += h.quantity
        portfolio_map[symbol]["total_cost"] += (h.quantity * h.avg_buy_price)
        # Atualiza preço atual (garante que usa o mais recente)
        portfolio_map[symbol]["current_price"] = curr_price

    # 2. Gerar a lista final baseada no mapa consolidado
    positions = []
    total_invested_market_value = 0.0

    for symbol, data in portfolio_map.items():
        qty = data["quantity"]
        if qty > 0:
            # Cálculo do Preço Médio Ponderado Global
            avg_buy_price_consolidated = data["total_cost"] / qty
            
            market_val = qty * data["current_price"]
            pnl = market_val - data["total_cost"]

            positions.append(schemas.PortfolioPosition(
                symbol=symbol, 
                quantity=qty, 
                avg_buy_price=avg_buy_price_consolidated,
                current_price=data["current_price"], 
                total_value=market_val, 
                profit_loss=pnl
            ))
            
            total_invested_market_value += market_val

    return schemas.PortfolioResponse(
        user_id=user_id, 
        total_net_worth=total_cash + total_invested_market_value,
        total_cash=total_cash, 
        total_invested=total_invested_market_value, 
        positions=positions
    )

@router.get("/history", response_model=List[schemas.HistoryPoint])
def get_net_worth_history(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    if not accounts: return []

    total_cash = sum(acc.current_balance for acc in accounts)
    
    holdings = db.query(models.Holding).filter(models.Holding.account_id.in_([a.id for a in accounts])).all()
    total_invested = sum(h.quantity * h.avg_buy_price for h in holdings)
    current_net_worth = total_cash + total_invested
    
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    transactions = db.query(models.Transaction).join(models.TransactionType).filter(models.Transaction.account_id.in_([a.id for a in accounts])).filter(models.Transaction.date >= start_date).all()
    
    history = []
    running = current_net_worth
    
    tx_map = {}
    for tx in transactions:
        d = tx.date.strftime("%Y-%m-%d")
        if d not in tx_map: tx_map[d] = []
        tx_map[d].append(tx)
        
    for i in range(30):
        target = end_date - timedelta(days=i)
        d_str = target.strftime("%Y-%m-%d")
        history.append(schemas.HistoryPoint(date=d_str, value=running))
        
        if d_str in tx_map:
            for tx in tx_map[d_str]:
                neg = ["Despesa", "Levantamento", "Compra"]
                if any(x in tx.transaction_type.name for x in neg): running += tx.amount
                else: running -= tx.amount
                
    return history[::-1]