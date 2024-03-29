from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {'text': 'Текст поста',
                  'group': 'Группа'}
        help_texts = {'text': 'Текст нового поста',
                      'group': 'Группа с текущим постом'}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("text",)
