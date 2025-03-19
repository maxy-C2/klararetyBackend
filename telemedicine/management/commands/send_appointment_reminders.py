# telemedicine/management/commands/send_appointment_reminders.py

from django.core.management.base import BaseCommand
from telemedicine.services.reminder_service import AppointmentReminderService

class Command(BaseCommand):
    """Django management command to send appointment reminders"""
    
    help = 'Send appointment reminders for upcoming appointments'

    def handle(self, *args, **options):
        """
        Execute the command to send appointment reminders
        
        This command retrieves upcoming appointments that need reminders
        and sends email reminders to patients.
        """
        reminder_service = AppointmentReminderService()
        appointments = reminder_service.get_upcoming_reminders()
        
        self.stdout.write(f"Found {appointments.count()} appointments requiring reminders")
        
        sent_count = 0
        for appointment in appointments:
            if reminder_service.send_reminder(appointment):
                sent_count += 1
                
        self.stdout.write(self.style.SUCCESS(
            f"Successfully sent {sent_count} appointment reminders"
        ))
