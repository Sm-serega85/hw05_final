import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
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
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=(
                b'\x47\x49\x46\x38\x39\x61\x01\x00'
                b'\x01\x00\x00\x00\x00\x21\xf9\x04'
                b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
                b'\x00\x00\x01\x00\x01\x00\x00\x02'
                b'\x02\x4c\x01\x00\x3b'
            ),
            content_type='image/gif'
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

        @classmethod
        def tearDownClass(cls):
            super().tearDownClass()
            shutil.rmtree(
                TEMP_MEDIA_ROOT, ignore_errors=True
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
            "group": PostFormTests.group.id,
            'image': self.uploaded,
        }
        self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)
        last = Post.objects.latest('id')
        self.assertEqual(last.text, form_data["text"])
        self.assertEqual(last.group, self.group)
        self.assertEqual(last.author, self.user)
        self.assertEqual(last.image, f'posts/{self.uploaded.name}')

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        posts_count = Post.objects.count()
        uploaded_1 = SimpleUploadedFile(
            name='small_1.gif',
            content=(
                b"\x47\x49\x46\x38\x39\x61\x02\x00"
                b"\x01\x00\x80\x00\x00\x00\x00\x00"
                b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
                b"\x00\x00\x00\x2C\x00\x00\x00\x00"
                b"\x02\x00\x01\x00\x00\x02\x02\x0C"
                b"\x0A\x00\x3B"
            ),
            content_type='image/gif'
        )
        form_data = {
            "text": "Изменяем текст",
            "group": self.group2.id,
            "image": uploaded_1,
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
        self.assertEqual(edited.image, f'posts/{uploaded_1.name}')

    def test_comment_correct_context(self):
        """Валидная форма Комментария создает запись в Post."""
        comments_count = Comment.objects.count()
        form_data = {"text": "Тестовый коммент"}
        response = self.authorized_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter
                        (text="Тестовый коммент").exists())
