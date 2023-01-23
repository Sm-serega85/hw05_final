from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="NoName")
        cls.user2 = User.objects.create(username="NoName2")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовый пост",
        )
        cls.post2 = Post.objects.create(
            author=cls.user2,
            text="Тестовый пост автора 2",
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)

    def test_urls_exists_at_desired_location(self):
        templates = [
            "/",
            f"/group/{self.group.slug}/",
            f"/profile/{self.user}/",
            f"/posts/{self.post.id}/",
        ]
        for adress in templates:
            with self.subTest(adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_post_id_edit_url_exists_at_author(self):
        """Страница /posts/post_id/edit/ доступна только автору."""
        response = self.authorized_client.get(f"/posts/{self.post.id}/edit/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page_at_desired_location(self):
        """Страница /unexisting_page/ не существует."""
        response = self.guest_client.get("/unexisting_page/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            "/": "posts/index.html",
            f"/group/{self.group.slug}/": "posts/group_list.html",
            f"/profile/{self.user.username}/": "posts/profile.html",
            f"/posts/{self.post.id}/": "posts/post_detail.html",
            f"/posts/{self.post.id}/edit/": "posts/create_post.html",
            "/create/": "posts/create_post.html",
        }
        for url, template in templates_url_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_create_url_redirect_anonymous_on_auth_login(self):
        """Страница /create/ недоступна неавторизованому клиенту."""
        response = self.guest_client.get("/create/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, "/auth/login/?next=/create/")

    def test_post_edit_url_redirect_anonymous_on_auth_login(self):
        """Страница /edit/ недоступна неавторизованному пользователю."""
        response = self.guest_client.get(f'/posts/{PostURLTests.post.id}'
                                         f'/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, f'/auth/login/?next='
                                       f'/posts/{PostURLTests.post.id}/edit/')

    def test_post_edit_url_redirect_not_author_on_post_view(self):
        """Страница /edit/ недоступна авториз. пользователю, не автору."""
        response = self.authorized_client.get(f'/posts/{PostURLTests.post2.id}'
                                              f'/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, f'/posts/{PostURLTests.post2.id}/')
