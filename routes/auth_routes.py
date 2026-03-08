from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from database.db import db
from database.models import User
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me')
        
        if not username or not password:
            flash('Please enter username and password', 'warning')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember_me)
            flash(f'Welcome back, {user.first_name or user.username}!', 'success')
            
            # Handle redirect after login
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Check for pending UPI analysis
            from flask import session
            if session.get('redirect_after_login') == 'main.upi_auth':
                if session.get('pending_analysis'):
                    # Create analysis record and redirect to UPI auth
                    from database.models import Analysis
                    pending_data = session.pop('pending_analysis')
                    
                    analysis = Analysis(
                        user_id=user.id,
                        investment_type=pending_data.get('investment_type'),
                        amount=float(pending_data.get('amount', 0)),
                        risk_tolerance=pending_data.get('risk_tolerance'),
                        horizon=pending_data.get('horizon')
                    )
                    db.session.add(analysis)
                    db.session.commit()
                    
                    session.pop('redirect_after_login')
                    return redirect(url_for('main.upi_auth', analysis_id=analysis.id))
                elif session.get('pending_upi_analysis_id'):
                    # Redirect to existing UPI analysis
                    analysis_id = session.pop('pending_upi_analysis_id')
                    session.pop('redirect_after_login')
                    return redirect(url_for('main.upi_auth', analysis_id=analysis_id))
            
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all fields', 'warning')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=full_name.split()[0] if full_name else '',
            last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password functionality"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # TODO: Send password reset email
            flash('Password reset instructions sent to your email', 'success')
        else:
            flash('Email not found', 'error')
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')
@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    user_id = current_user.id
    user = User.query.get(user_id)
    logout_user()
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('Your account has been deleted.', 'success')
    return redirect(url_for('auth.register'))
