from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User

User = get_user_model()


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="UserTest")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.group2 = Group.objects.create(
            title="Тестовая группа 2",
            slug="test-slug-2",
            description="Тестовое описание 2",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовый текст",
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст",
            "group": self.group.id
        }
        self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)

        last = Post.objects.latest('id')
        self.assertEqual(last.text, form_data["text"])
        self.assertEqual(last.group, self.group)
        self.assertEqual(last.author, self.user)

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            "text": "Изменяем текст",
            "group": self.group2.id
        }
        self.authorized_client.post(
            reverse("posts:post_edit", args=({self.post.id})),
            data=form_data,
            follow=True,
        )

        self.assertEqual(Post.objects.count(), posts_count)

        edited = Post.objects.filter(id=self.post.id).first()
        self.assertEqual(edited.text, form_data["text"])
        self.assertEqual(edited.group, self.group2)
        self.assertEqual(edited.author, self.user)
