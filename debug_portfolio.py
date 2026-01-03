from app.database.database import SessionLocal
from app.models import User, Account, Holding, Asset, AssetPrice
from sqlalchemy import desc

def debug_portfolio(email):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        print(f"User {email} not found")
        return

    print(f"--- Portfolio Debug for {user.email} ({user.role}) ---")
    
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    print(f"Accounts: {[a.name for a in accounts]}")
    
    account_ids = [acc.id for acc in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()
    
    print(f"Holdings Found: {len(holdings)}")
    
    for h in holdings:
        asset = db.query(Asset).filter(Asset.id == h.asset_id).first()
        print(f"  - {asset.symbol}: Qty={h.quantity}, AvgPrice={h.avg_buy_price}")
        
        latest_price = db.query(AssetPrice).filter(
            AssetPrice.asset_id == h.asset_id
        ).order_by(desc(AssetPrice.date)).first()
        
        price = latest_price.close_price if latest_price else "NO PRICE (Using Avg)"
        print(f"    Current Price in DB: {price}")

if __name__ == "__main__":
    debug_portfolio("premium@moneymap.com")
    debug_portfolio("basic@moneymap.com")