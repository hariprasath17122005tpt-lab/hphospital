from datetime import datetime
import io

import pandas as pd
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required
from functools import wraps
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.models.models import db, Medicine, UserRole


pharmacy_bp = Blueprint('pharmacy', __name__, url_prefix='/pharmacy')

EXPECTED_UPLOAD_COLUMNS = {
    'medicine_name',
    'brand',
    'category',
    'price',
    'stock',
    'supplier',
}


def pharmacist_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access pharmacy medicine management.', 'danger')
            return redirect(url_for('auth.staff_login', role='PHARMACIST'))
        allowed = {UserRole.PHARMACIST, UserRole.HOST, UserRole.ADMIN}
        if current_user.role not in allowed:
            flash('Access denied. Pharmacist login required.', 'danger')
            return redirect(url_for('auth.staff_login', role='PHARMACIST', switch='1'))
        return f(*args, **kwargs)
    return decorated


def _clean_text(value):
    if value is None:
        return ''
    text = str(value).strip()
    if not text or text.lower() == 'nan':
        return ''
    return text


def _to_float(value):
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    return float(cleaned)


def _to_int(value, default=0):
    cleaned = _clean_text(value)
    if not cleaned:
        return default
    return int(float(cleaned))


def _medicine_by_name_brand(name, brand=None):
    """Check for duplicate medicine by name AND brand (UNIQUE constraint is on both).
    
    Database UNIQUE constraint: ('name', 'brand', name='unique_medicine')
    So same name with different brands = different medicines.
    Same name with same brand = duplicate (should update).
    """
    if not name:
        return None
    
    # Normalize inputs
    clean_name = name.strip() if name else ''
    clean_brand = brand.strip() if brand else None
    
    # Query: find medicine with same name (case-insensitive) AND same brand
    query = Medicine.query.filter(
        func.lower(func.trim(Medicine.name)) == clean_name.lower()
    )
    
    # For brand: if provided and not empty, match it; otherwise match empty/NULL
    if clean_brand:
        # Brand is provided - match after trim + casefold so old trailing-space data
        # still maps to the same unique (name, brand) key.
        query = query.filter(
            func.lower(func.trim(func.coalesce(Medicine.brand, ''))) == clean_brand.lower()
        )
    else:
        # No brand provided - match medicines with NULL or empty brand
        query = query.filter(
            or_(
                Medicine.brand.is_(None),
                func.trim(Medicine.brand) == ''
            )
        )
    
    return query.first()


@pharmacy_bp.route('/manage', methods=['GET'])
@login_required
@pharmacist_access_required
def manage_medicines():
    return render_template('pharmacy/manage_medicines.html')


@pharmacy_bp.route('/upload-medicines', methods=['POST'])
@login_required
@pharmacist_access_required
def upload_medicines():
    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    filename = uploaded_file.filename.lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.csv')):
        return jsonify({'success': False, 'error': 'Invalid file. Upload .xlsx or .csv only'}), 400

    try:
        if filename.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            raw = uploaded_file.read()
            df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        return jsonify({'success': False, 'error': f'Unable to read file: {exc}'}), 400

    normalized_columns = {str(c).strip().lower() for c in df.columns}
    missing = sorted(EXPECTED_UPLOAD_COLUMNS - normalized_columns)
    if missing:
        return jsonify({
            'success': False,
            'error': f'Missing required columns: {", ".join(missing)}',
        }), 400

    # Align input keys to lowercase names expected by logic.
    df.columns = [str(c).strip().lower() for c in df.columns]

    inserted = 0
    updated = 0

    try:
        for _, row in df.iterrows():
            medicine_name = _clean_text(row.get('medicine_name'))
            brand = _clean_text(row.get('brand'))
            category = _clean_text(row.get('category'))
            supplier = _clean_text(row.get('supplier'))
            expiry_date = _clean_text(row.get('expiry_date'))
            batch_number = _clean_text(row.get('batch_number'))
            manufacturer = _clean_text(row.get('manufacturer'))

            # Skip empty rows safely.
            if not medicine_name:
                continue

            try:
                price = _to_float(row.get('price'))
                stock_delta = _to_int(row.get('stock'), default=0)
            except Exception:
                # Skip invalid numeric rows safely.
                continue

            existing = _medicine_by_name_brand(medicine_name, brand)
            if existing:
                existing.stock = (existing.stock or 0) + max(stock_delta, 0)
                if price is not None:
                    existing.price = price
                if category:
                    existing.category = category
                if supplier:
                    existing.supplier = supplier
                if expiry_date:
                    existing.expiry_date = expiry_date
                if batch_number:
                    existing.batch_number = batch_number
                if manufacturer:
                    existing.manufacturer = manufacturer
                updated += 1
            else:
                med = Medicine(
                    name=medicine_name,
                    brand=brand or None,
                    category=category or None,
                    price=price,
                    stock=max(stock_delta, 0),
                    supplier=supplier or None,
                    expiry_date=expiry_date or None,
                    batch_number=batch_number or None,
                    manufacturer=manufacturer or None,
                    created_at=datetime.utcnow(),
                )
                db.session.add(med)
                inserted += 1

        db.session.commit()
        return jsonify({'success': True, 'inserted': inserted, 'updated': updated})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Upload failed: {exc}'}), 500


@pharmacy_bp.route('/search', methods=['GET'])
@login_required
@pharmacist_access_required
def search_medicines():
    """Search medicines for autocomplete - returns JSON list.
    Falls back to a built-in catalog when the DB has no matches."""
    q = _clean_text(request.args.get('q', ''))
    if len(q) < 2:
        return jsonify([])

    try:
        matches = (
            Medicine.query
            .filter(Medicine.name.ilike(f'%{q}%'))
            .order_by(Medicine.name.asc())
            .limit(10)
            .all()
        )
        if matches:
            return jsonify([
                {
                    'id': m.id,
                    'name': m.name,
                    'brand': m.brand or '',
                    'category': m.category or '',
                    'price': float(m.price) if m.price else 0,
                    'stock': int(m.stock) if m.stock else 0,
                    'supplier': m.supplier or '',
                }
                for m in matches
            ])
    except Exception as exc:
        print(f"Search error: {exc}")

    # Fallback: use built-in medicine catalog
    from app.routes.features import _BUILTIN_MEDICINE_CATALOG
    q_lower = q.lower()
    fallback = [
        m for m in _BUILTIN_MEDICINE_CATALOG
        if q_lower in m['name'].lower()
           or q_lower in m.get('brand', '').lower()
           or q_lower in m.get('category', '').lower()
    ]
    fallback.sort(key=lambda m: (
        0 if m['name'].lower().startswith(q_lower) else 1,
        len(m['name']),
        m['name']
    ))
    return jsonify(fallback[:10])


@pharmacy_bp.route('/add-medicine', methods=['POST'])
@login_required
@pharmacist_access_required
def add_medicine():
    from sqlalchemy.exc import IntegrityError
    
    payload = request.get_json(silent=True) or request.form
    name = _clean_text(payload.get('name'))
    brand = _clean_text(payload.get('brand'))
    category = _clean_text(payload.get('category'))
    supplier = _clean_text(payload.get('supplier'))
    expiry_date = _clean_text(payload.get('expiry_date'))
    batch_number = _clean_text(payload.get('batch_number'))
    manufacturer = _clean_text(payload.get('manufacturer'))

    if not name:
        return jsonify({'success': False, 'error': 'Medicine name is required'}), 400

    try:
        price = _to_float(payload.get('price') or payload.get('unit_price'))
        stock = _to_int(payload.get('stock'), default=0)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid price or stock value'}), 400

    # Check for duplicates BEFORE inserting (check by BOTH name and brand)
    existing = _medicine_by_name_brand(name, brand)
    if existing:
        # If it already exists with same name+brand, update stock instead of creating duplicate
        try:
            old_stock = existing.stock or 0
            existing.stock = old_stock + stock
            if price is not None:
                existing.unit_price = price
            if category:
                existing.category = category
            if supplier:
                existing.supplier = supplier
            if expiry_date:
                existing.expiry_date = expiry_date
            if batch_number:
                existing.batch_number = batch_number
            if manufacturer:
                existing.manufacturer = manufacturer
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'[OK] Updated existing medicine: added {stock} units to "{existing.name}" (total: {existing.stock} units)',
                'medicine': {
                    'id': existing.id,
                    'name': existing.name,
                    'brand': existing.brand,
                    'category': existing.category,
                    'price': existing.unit_price,
                    'stock': existing.stock,
                    'supplier': existing.supplier,
                }
            }), 200
        except Exception as exc:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Failed to update medicine: {str(exc)}'}), 500

    try:
        med = Medicine(
            name=name,
            brand=brand or None,
            category=category or None,
            unit_price=price,
            stock=max(stock, 0),
            supplier=supplier or None,
            expiry_date=expiry_date or None,
            batch_number=batch_number or None,
            manufacturer=manufacturer or None,
            created_at=datetime.utcnow(),
        )
        db.session.add(med)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'[OK] New medicine "{med.name}" added with {med.stock} units',
            'medicine': {
                'id': med.id,
                'name': med.name,
                'brand': med.brand,
                'category': med.category,
                'price': med.unit_price,
                'stock': med.stock,
                'supplier': med.supplier,
            }
        }), 201
    except IntegrityError as exc:
        db.session.rollback()
        # Handle unique constraint violation (name + brand combo)
        if 'unique' in str(exc).lower():
            # Try to find and update the existing medicine by BOTH name and brand
            try:
                existing = _medicine_by_name_brand(name, brand)
                if existing:
                    old_stock = existing.stock or 0
                    existing.stock = old_stock + stock
                    if price is not None:
                        existing.unit_price = price
                    if category:
                        existing.category = category
                    db.session.commit()
                    return jsonify({
                        'success': True,
                        'message': f'[OK] Updated: added {stock} units to "{existing.name}" (total: {existing.stock} units)',
                        'medicine': {
                            'id': existing.id,
                            'name': existing.name,
                            'stock': existing.stock,
                        }
                    }), 200
            except Exception:
                db.session.rollback()
                pass
            return jsonify({'success': False, 'error': 'This medicine with this brand already exists. Please add stock instead.'}), 409
        return jsonify({'success': False, 'error': f'Database error: {str(exc)}'}), 500
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to add medicine: {str(exc)}'}), 500


@pharmacy_bp.route('/add-stock', methods=['POST'])
@login_required
@pharmacist_access_required
def add_stock():
    """Add stock to existing medicine via modal"""
    payload = request.get_json(silent=True) or request.form
    med_id = payload.get('medicine_id')
    qty = payload.get('quantity')
    notes = _clean_text(payload.get('notes', ''))

    if not med_id:
        return jsonify({'success': False, 'error': 'Medicine ID is required'}), 400

    try:
        mid = int(med_id)
        quantity = int(qty)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid medicine_id or quantity'}), 400

    if quantity < 1:
        return jsonify({'success': False, 'error': 'Quantity must be at least 1'}), 400

    try:
        med = Medicine.query.get(mid)
        if not med:
            return jsonify({'success': False, 'error': 'Medicine not found'}), 404

        # Add stock
        old_stock = med.stock or 0
        med.stock = old_stock + quantity

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {quantity} units to {med.name}',
            'medicine': {
                'id': med.id,
                'name': med.name,
                'brand': med.brand,
                'old_stock': old_stock,
                'new_stock': med.stock,
            }
        }), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to add stock: {exc}'}), 500
