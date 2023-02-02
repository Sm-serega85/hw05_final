import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="StasBasov")
        cls.user_1 = User.objects.create_user(username='noname')
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
            text="Тестовый пост",
            group=cls.group
        )
        cls.post_1 = Post.objects.create(
            author=cls.user_1,
            text='Тестовый пост другого автора',
            group=cls.group2
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user_1,
            text='Тестовый комментарий'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(self.user_1)
        self.pages = [
            reverse("posts:index"),
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ),
            reverse(
                "posts:profile", kwargs={"username": self.user}
            )
        ]
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse("posts:index"): "posts/index.html",
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): "posts/group_list.html",
            reverse(
                "posts:profile", kwargs={"username": self.user}
            ): "posts/profile.html",
            reverse(
                "posts:post_detail", kwargs={"post_id": self.post.id}
            ): "posts/post_detail.html",
            reverse(
                "posts:post_edit", kwargs={"post_id": self.post.id}
            ): "posts/create_post.html",
            reverse("posts:post_create"): "posts/create_post.html",
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def test_index_show_correct_context(self):
        """Список постов в шаблоне index равен ожидаемому контексту."""
        response = self.guest_client.get(reverse("posts:index"))
        expected = list(Post.objects.all()[:10])
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_group_list_show_correct_context(self):
        """Список постов в шаблоне group_list равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        expected = list(Post.objects.filter(group_id=self.group.id)[:10])
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse("posts:profile", args=(self.user,))
        )
        expected = list(Post.objects.filter(author_id=self.user.id)[:10])
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""

        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )

        responsepost = response.context.get("post")
        self.assertEqual(responsepost.text, self.post.text)
        self.assertEqual(responsepost.author, self.post.author)
        self.assertEqual(responsepost.group, self.post.group)

    def test_create_edit_show_correct_context(self):
        """Шаблон create_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на странице с выбранной группой"""
        expected = list(Post.objects.filter(group=self.group)[:10])
        page = reverse("posts:group_list", kwargs={"slug": self.group.slug})
        response = self.authorized_client.get(page)
        self.assertEqual(expected, list(response.context["page_obj"]))

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный пост с группой не попал в чужую группу."""
        page = reverse("posts:group_list", kwargs={"slug": self.group2.slug})
        response = self.authorized_client.get(page)
        pageposts = list(response.context["page_obj"])
        self.assertNotIn(self.post, pageposts)

    def test_paginator(self):
        """Проверка пагинатора."""
        new_posts = [
            Post(
                author=self.user,
                text=f'тестовый пост {i}',
                group=self.group
            ) for i in range(1, 13)
        ]
        Post.objects.all().delete()
        Post.objects.bulk_create(new_posts)

        pages_posts = [
            (1, 10),
            (2, 2)
        ]

        for page in self.pages:
            for pagepost in pages_posts:
                with self.subTest(value=page):
                    response = self.client.get(page + f'?page={pagepost[0]}')
                    self.assertEqual(len(response.context['page_obj']),
                                     pagepost[1])

    def test_check_cache(self):
        """Проверка кеша."""
        response = self.guest_client.get(reverse("posts:index"))
        Post.objects.get(id=self.post.id).delete()
        response2 = self.guest_client.get(reverse("posts:index"))
        self.assertEqual(response.content, response2.content)
        cache.clear()
        response3 = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, response3.content)

    def test_author_subscription(self):
        """Проверка подписки на автора поста"""
        sub_1 = Follow.objects.filter(
            author=self.post_1.author, user=self.user
        )
        self.assertFalse(sub_1)
        self.authorized_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_1.username})
        )
        sub_2 = Follow.objects.filter(
            author=self.post_1.author, user=self.user
        )
        self.assertTrue(sub_2)

    def test_author_unsubscription(self):
        """Проверка отписки от автора"""
        Follow.objects.create(
            user=self.user,
            author=self.user_1
        )
        sub_1 = Follow.objects.filter(
            author=self.post_1.author, user=self.user
        )
        self.assertTrue(sub_1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user_1.username}
            )
        )
        sub_2 = Follow.objects.filter(
            author=self.post_1.author, user=self.user
        )
        self.assertFalse(sub_2)

    def test_subscription_added_to_profile_follow(self):
        """Пост появляется на странице подписок у подписчика"""
        self.authorized_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_1.username})
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user_1.username}
            )
        )

    def test_subscription_no_added_to_profile_follow_user(self):
        """Пост НЕ появляется на странице подписок у НЕ подписчика"""
        sub_1 = Follow.objects.filter(
            author=self.post_1.author, user=self.user
        )
        self.assertFalse(sub_1)
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user.username})
        )
        response = self.authorized_client_1.get(
            reverse(
                'posts:follow_index',
            )
        )
        self.assertNotIn(self.post_1, response.context['page_obj'])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TaskPagesTests, cls).setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.group = Group.objects.create(
            title="Test group",
            slug="test_group_slug",
            description="Test group description",
        )
        cls.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.uploaded = SimpleUploadedFile(
            name="small.gif", content=cls.small_gif, content_type="image/gif"
        )
        cls.post = Post.objects.create(
            author=cls.user, text="Тестовый текст",
            group=cls.group, image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()

    def test_image_in_index_and_profile_page(self):
        """Картинка передается на страницу index_and_profile."""
        templates = (
            reverse("posts:index"),
            reverse("posts:profile", kwargs={"username": self.post.author}),
            reverse("posts:group_list", kwargs={"slug": self.group.slug}),
        )
        for url in templates:
            with self.subTest(url):
                response = self.guest_client.get(url)
                obj = response.context["page_obj"][0]
                self.assertEqual(obj.image, self.post.image)

    def test_image_in_post_detail_page(self):
        """Картинка передается на страницу post_detail."""
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        obj = response.context["post"]
        self.assertEqual(obj.image, self.post.image)
