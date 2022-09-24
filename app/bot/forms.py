from django import forms
from bot.models import *




class BroadcastForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    mailing_name = forms.CharField(
        label='Название рассылки',
        widget=forms.TextInput
    )
    message_text = forms.CharField(
        label='Текст сообщения',
        widget=forms.Textarea
    )
    message_type = forms.ChoiceField(
        label='Тип сообщения',
        choices=[('SIMPLE_TEXT', 'Простой текст'), ('FLY_BTN', 'Чат. Кнопка'), ('POLL', 'Опрос')]
    )
    files = forms.ModelMultipleChoiceField(
        label='Выбирете существующие файлы для рассылки',
        queryset=File.objects.all(),
        required=False
        
    )
    users = forms.ModelMultipleChoiceField(
        label='Пользователи для рассылки',
        queryset=User.objects.all()
    )


    def save(self):
        name = self.cleaned_data['mailing_name']
        message = Message(
            name=name, 
            text=self.cleaned_data['message_text'],
            message_type=self.cleaned_data['message_type'],
        )
        message.save()
        message.files.set(self.cleaned_data['files'])
        message.save()
        broadcast = Broadcast(
            name=name, message=message,
        )
        broadcast.save()
        broadcast.users.set(self.cleaned_data['users'])
        broadcast.save()
        return broadcast
