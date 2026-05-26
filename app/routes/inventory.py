"""Medical Inventory & Supplies Management Module"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, InventoryItem, InventoryTransaction, UserRole)
from datetime import datetime, timedelta
from sqlalchemy import func

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


def _staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.doctor_login'))
        role_val = getattr(current_user.role, 'value', str(current_user.role)).upper()
        if role_val not in ('HOST', 'ADMIN', 'PHARMACIST', 'NURSE'):
            flash('Access denied.', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@inventory_bp.route('/')
@inventory_bp.route('/dashboard')
@login_required
@_staff_required
def dashboard():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')

    query = InventoryItem.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(InventoryItem.item_name.ilike(f'%{search}%'))

    items = query.order_by(InventoryItem.item_name).all()

    if status_filter:
        items = [i for i in items if i.stock_status == status_filter]

    categories = db.session.query(InventoryItem.category).filter_by(is_active=True).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    stats = {
        'total_items': InventoryItem.query.filter_by(is_active=True).count(),
        'out_of_stock': len([i for i in InventoryItem.query.filter_by(is_active=True).all() if i.stock_status == 'Out of Stock']),
        'critical': len([i for i in InventoryItem.query.filter_by(is_active=True).all() if i.stock_status == 'Critical']),
        'low_stock': len([i for i in InventoryItem.query.filter_by(is_active=True).all() if i.stock_status == 'Low']),
        'total_value': db.session.query(
            func.coalesce(func.sum(InventoryItem.current_stock * InventoryItem.unit_price), 0)
        ).filter_by(is_active=True).scalar(),
    }

    return render_template('inventory/dashboard.html',
                           items=items, categories=categories,
                           stats=stats, current_category=category,
                           current_search=search, current_status=status_filter)


@inventory_bp.route('/add', methods=['GET', 'POST'])
@login_required
@_staff_required
def add_item():
    if request.method == 'POST':
        try:
            item_code = request.form.get('item_code') or f"INV-{datetime.utcnow().strftime('%y%m%d')}-{InventoryItem.query.count()+1:04d}"
            item = InventoryItem(
                item_name=request.form.get('item_name'),
                item_code=item_code,
                category=request.form.get('category'),
                sub_category=request.form.get('sub_category'),
                unit=request.form.get('unit', 'Piece'),
                unit_price=request.form.get('unit_price', 0, type=float),
                current_stock=request.form.get('current_stock', 0, type=int),
                minimum_stock=request.form.get('minimum_stock', 10, type=int),
                reorder_level=request.form.get('reorder_level', 20, type=int),
                location=request.form.get('location'),
                supplier=request.form.get('supplier'),
                manufacturer=request.form.get('manufacturer'),
                is_active=True,
                last_restocked=datetime.utcnow()
            )
            db.session.add(item)
            db.session.commit()

            if item.current_stock > 0:
                txn = InventoryTransaction(
                    item_id=item.id,
                    transaction_type='Purchase',
                    quantity=item.current_stock,
                    unit_price=item.unit_price,
                    reference='Initial Stock',
                    performed_by=current_user.id
                )
                db.session.add(txn)
                db.session.commit()

            flash('Item added to inventory!', 'success')
            return redirect(url_for('inventory.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')

    return render_template('inventory/add_item.html')


@inventory_bp.route('/api/stock-update', methods=['POST'])
@login_required
@_staff_required
def stock_update():
    data = request.get_json(silent=True) or {}
    item = InventoryItem.query.get(data.get('item_id'))
    if not item:
        return jsonify({'success': False, 'error': 'Item not found'}), 404

    txn_type = data.get('type', 'Purchase')
    quantity = data.get('quantity', 0)

    if txn_type in ('Purchase', 'Return'):
        item.current_stock += quantity
        item.last_restocked = datetime.utcnow()
    elif txn_type in ('Issue', 'Expired', 'Damage'):
        if item.current_stock < quantity:
            return jsonify({'success': False, 'error': 'Insufficient stock'}), 400
        item.current_stock -= quantity
    elif txn_type == 'Adjustment':
        item.current_stock = quantity

    txn = InventoryTransaction(
        item_id=item.id,
        transaction_type=txn_type,
        quantity=quantity,
        unit_price=data.get('unit_price', item.unit_price),
        reference=data.get('reference', ''),
        remarks=data.get('remarks', ''),
        performed_by=current_user.id
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({'success': True, 'new_stock': item.current_stock, 'status': item.stock_status})


@inventory_bp.route('/item/<int:item_id>')
@login_required
@_staff_required
def view_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    transactions = InventoryTransaction.query.filter_by(item_id=item_id).order_by(
        InventoryTransaction.created_at.desc()
    ).limit(50).all()
    return render_template('inventory/view_item.html', item=item, transactions=transactions)


@inventory_bp.route('/api/search')
@login_required
def search_items():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    items = InventoryItem.query.filter(
        InventoryItem.item_name.ilike(f'%{q}%'),
        InventoryItem.is_active == True
    ).limit(10).all()
    return jsonify([{
        'id': i.id,
        'name': i.item_name,
        'code': i.item_code,
        'stock': i.current_stock,
        'status': i.stock_status,
        'category': i.category
    } for i in items])
