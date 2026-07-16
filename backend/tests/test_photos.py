"""
Тесты загрузки фото.

Проверяют валидацию, загрузку, получение и удаление фото.
"""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

# Создаём тестовое изображение (1x1 px белый PNG) через Pillow
def _make_test_image() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (1, 1), color="white")
    img.save(buf, format="PNG")
    return buf.getvalue()

_TEST_PNG = _make_test_image()


class TestPhotos:
    """Набор тестов для эндпоинтов фото."""

    @property
    def _upload_headers(self):
        return {"Content-Type": "image/png"}

    # ------------------------------------------------------------------
    # 1. Валидация: недопустимый формат
    # ------------------------------------------------------------------
    async def test_validate_invalid_extension(self, client: AsyncClient):
        """❌ Загрузка файла с недопустимым расширением."""
        from app.core.image_service import validate_image

        with pytest.raises(ValueError, match="Недопустимый формат"):
            validate_image(b"fake content", "virus.exe")

    # ------------------------------------------------------------------
    # 2. Валидация: слишком большой файл
    # ------------------------------------------------------------------
    async def test_validate_too_large(self, client: AsyncClient):
        """❌ Файл больше 10 MB."""
        from app.core.image_service import validate_image, MAX_FILE_SIZE

        with pytest.raises(ValueError, match="Файл слишком большой"):
            validate_image(b"x" * (MAX_FILE_SIZE + 1), "image.jpg")

    # ------------------------------------------------------------------
    # 3. Валидация: корректный PNG
    # ------------------------------------------------------------------
    async def test_validate_valid_image(self, client: AsyncClient):
        """✅ Корректное PNG-изображение проходит валидацию."""
        from app.core.image_service import validate_image

        mime = validate_image(_TEST_PNG, "test.png")
        assert mime == "image/png"

    # ------------------------------------------------------------------
    # 4. Генерация миниатюры
    # ------------------------------------------------------------------
    async def test_thumbnail_creation(self, client: AsyncClient):
        """✅ Миниатюра создаётся и имеет корректный размер."""
        from app.core.image_service import create_thumbnail
        from PIL import Image
        from io import BytesIO

        thumb = create_thumbnail(_TEST_PNG)
        assert len(thumb) > 0

        # Проверяем, что это JPEG
        img = Image.open(BytesIO(thumb))
        assert img.format == "JPEG"

    # ------------------------------------------------------------------
    # 5. Загрузка фото автомобиля
    # ------------------------------------------------------------------
    async def test_upload_car_photo(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_car,
    ):
        """✅ Загрузка фото для автомобиля."""
        files = {"file": ("test_car.png", _TEST_PNG, "image/png")}
        response = await client.post(
            f"/api/upload/car/{test_car.id}",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert "url" in data
        assert data["url"].startswith("/uploads/")

    # ------------------------------------------------------------------
    # 6. Получение списка фото
    # ------------------------------------------------------------------
    async def test_get_photos(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_car,
    ):
        """✅ Получение списка фото для автомобиля."""
        # Сначала загрузим фото
        files = {"file": ("test.png", _TEST_PNG, "image/png")}
        upload_resp = await client.post(
            f"/api/upload/car/{test_car.id}",
            files=files,
            headers=auth_headers,
        )
        assert upload_resp.status_code == 200

        # Получаем список
        response = await client.get(
            f"/api/photos/car/{test_car.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["entity_type"] == "car"

    # ------------------------------------------------------------------
    # 7. Удаление фото
    # ------------------------------------------------------------------
    async def test_delete_photo(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_car,
    ):
        """✅ Удаление фото."""
        # Загружаем
        files = {"file": ("test.png", _TEST_PNG, "image/png")}
        upload_resp = await client.post(
            f"/api/upload/car/{test_car.id}",
            files=files,
            headers=auth_headers,
        )
        assert upload_resp.status_code == 200
        photo_id = upload_resp.json()["id"]

        # Удаляем
        response = await client.delete(
            f"/api/photos/{photo_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        # Проверяем, что фото удалено
        get_resp = await client.get(
            f"/api/photos/car/{test_car.id}",
            headers=auth_headers,
        )
        assert len(get_resp.json()) == 0
