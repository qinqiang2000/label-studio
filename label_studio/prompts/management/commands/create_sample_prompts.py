from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from prompts.models import Prompt

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample prompts for testing'

    def handle(self, *args, **options):
        # Get or create a user
        user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            user.set_password('admin')
            user.save()
            self.stdout.write(f'Created user: {user.email}')
        else:
            self.stdout.write(f'Using existing user: {user.email}')

        # Sample prompts
        sample_prompts = [
            {
                'name': 'Text Classification Prompt',
                'description': 'A prompt for classifying text sentiment',
                'content': '''Analyze the sentiment of the following text and classify it as positive, negative, or neutral.

Text: {text}

Classification:'''
            },
            {
                'name': 'Entity Extraction Prompt',
                'description': 'A prompt for extracting named entities from text',
                'content': '''Extract all named entities from the following text. Identify person names, organizations, locations, and dates.

Text: {text}

Entities:
- Persons:
- Organizations:
- Locations:
- Dates:'''
            },
            {
                'name': 'Summarization Prompt',
                'description': 'A prompt for generating text summaries',
                'content': '''Please provide a concise summary of the following text in 2-3 sentences:

Text: {text}

Summary:'''
            },
            {
                'name': 'Question Answering Prompt',
                'description': 'A prompt for answering questions based on context',
                'content': '''Based on the following context, answer the question accurately and concisely.

Context: {context}

Question: {question}

Answer:'''
            },
            {
                'name': 'Translation Prompt',
                'description': 'A prompt for translating text to different languages',
                'content': '''Translate the following text from {source_language} to {target_language}:

Original text: {text}

Translation:'''
            }
        ]

        created_count = 0
        for prompt_data in sample_prompts:
            prompt, created = Prompt.objects.get_or_create(
                name=prompt_data['name'],
                created_by=user,
                defaults={
                    'description': prompt_data['description'],
                    'content': prompt_data['content']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created prompt: {prompt.name}')
            else:
                self.stdout.write(f'Prompt already exists: {prompt.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new sample prompts')
        ) 