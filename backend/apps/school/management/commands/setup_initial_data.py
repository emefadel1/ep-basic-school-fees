# apps/school/management/commands/setup_initial_data.py

"""
Management command to set up initial school data.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.school.models import SchoolClass, SchoolSettings, Category
from apps.users.models import User
from decimal import Decimal


class Command(BaseCommand):
    help = 'Set up initial school data (classes, settings, admin user)'
    
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')
        
        # Create school settings
        self.create_school_settings()
        
        # Create classes
        self.create_classes()
        
        # Create admin user
        self.create_admin_user()
        
        self.stdout.write(self.style.SUCCESS('Initial data setup complete!'))
    
    def create_school_settings(self):
        settings, created = SchoolSettings.objects.get_or_create(pk=1)
        if created:
            self.stdout.write('  Created school settings')
        else:
            self.stdout.write('  School settings already exist')
    
    def create_classes(self):
        classes_data = [
            # Pre-School
            {'code': 'N1', 'name': 'Nursery 1', 'category': Category.PRE_SCHOOL, 
             'daily_fee': Decimal('3.00'), 'sort_order': 1},
            {'code': 'N2', 'name': 'Nursery 2', 'category': Category.PRE_SCHOOL, 
             'daily_fee': Decimal('3.00'), 'sort_order': 2},
            {'code': 'KG1', 'name': 'Kindergarten 1', 'category': Category.PRE_SCHOOL, 
             'daily_fee': Decimal('3.00'), 'sort_order': 3},
            {'code': 'KG2', 'name': 'Kindergarten 2', 'category': Category.PRE_SCHOOL, 
             'daily_fee': Decimal('3.00'), 'sort_order': 4},
            
            # Lower Primary
            {'code': 'B1', 'name': 'Basic 1', 'category': Category.PRIMARY, 
             'daily_fee': Decimal('4.00'), 'sort_order': 5},
            {'code': 'B2', 'name': 'Basic 2', 'category': Category.PRIMARY, 
             'daily_fee': Decimal('4.00'), 'sort_order': 6},
            {'code': 'B3', 'name': 'Basic 3', 'category': Category.PRIMARY, 
             'daily_fee': Decimal('4.00'), 'sort_order': 7},
            
            # Upper Primary
            {'code': 'B4', 'name': 'Basic 4', 'category': Category.PRIMARY, 
             'daily_fee': Decimal('5.00'), 'sort_order': 8},
            {'code': 'B5', 'name': 'Basic 5', 'category': Category.PRIMARY, 
             'daily_fee': Decimal('5.00'), 'sort_order': 9},
            {'code': 'B6', 'name': 'Basic 6', 'category': Category.PRIMARY, 
             'daily_fee': Decimal('5.00'), 'sort_order': 10},
            
            # JHS
            {'code': 'B7', 'name': 'JHS 1', 'category': Category.JHS, 
             'daily_fee': Decimal('5.00'), 'jhs_extra_fee': Decimal('2.00'), 
             'sort_order': 11},
            {'code': 'B8', 'name': 'JHS 2', 'category': Category.JHS, 
             'daily_fee': Decimal('5.00'), 'jhs_extra_fee': Decimal('2.00'), 
             'sort_order': 12},
            {'code': 'B9', 'name': 'JHS 3', 'category': Category.JHS, 
             'daily_fee': Decimal('5.00'), 'jhs_extra_fee': Decimal('3.00'), 
             'jhs3_extra_fee': Decimal('2.00'), 'sort_order': 13},
        ]
        
        created_count = 0
        for class_data in classes_data:
            _, created = SchoolClass.objects.get_or_create(
                code=class_data['code'],
                defaults=class_data
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'  Created {created_count} classes')
    
    def create_admin_user(self):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@epbasic.edu.gh',
                password='admin123',  # Change this!
                first_name='System',
                last_name='Administrator',
                role=User.Role.BURSAR
            )
            self.stdout.write('  Created admin user (username: admin, password: admin123)')
            self.stdout.write(self.style.WARNING('  IMPORTANT: Change the admin password immediately!'))
        else:
            self.stdout.write('  Admin user already exists')