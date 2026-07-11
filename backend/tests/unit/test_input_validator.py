from unittest.mock import MagicMock

import pytest

from app.orchestrator.input_validator import InputValidator, ValidationError


@pytest.fixture
def validator():
    return InputValidator()


@pytest.fixture
def valid_user():
    user = MagicMock()
    user.id = 1
    user.is_active = True
    return user


@pytest.fixture
def sample_file(tmp_dir):
    path = tmp_dir / "valid_image.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return path


class TestCropValidation:
    def test_supported_crops_contain_all_trained_models(self, validator):
        expected = {"rice", "tomato", "potato", "pepper"}
        assert expected.issubset(validator.SUPPORTED_CROPS)

    def test_valid_crop_override_accepted(self, validator, valid_user, sample_file):
        result = validator.validate(
            state={}, user=valid_user, image_path=str(sample_file), crop_override="Rice"
        )
        assert result.crop_override == "Rice"

    def test_crop_override_case_insensitive(self, validator, valid_user, sample_file):
        result = validator.validate(
            state={}, user=valid_user, image_path=str(sample_file), crop_override="tomato"
        )
        assert result.crop_override == "Tomato"

    def test_unsupported_crop_raises(self, validator, valid_user, sample_file):
        with pytest.raises(ValidationError, match="Unsupported crop"):
            validator.validate(
                state={}, user=valid_user, image_path=str(sample_file), crop_override="Mango"
            )

    def test_no_crop_override_passes(self, validator, valid_user, sample_file):
        result = validator.validate(state={}, user=valid_user, image_path=str(sample_file))
        assert result.crop_override is None


class TestFileValidation:
    def test_missing_user_raises(self, validator, sample_file):
        with pytest.raises(ValidationError, match="User is required"):
            validator.validate(state={}, user=None, image_path=str(sample_file))

    def test_inactive_user_raises(self, validator, sample_file):
        user = MagicMock()
        user.id = 1
        user.is_active = False
        with pytest.raises(ValidationError, match="inactive"):
            validator.validate(state={}, user=user, image_path=str(sample_file))

    def test_empty_image_path_raises(self, validator, valid_user):
        with pytest.raises(ValidationError, match="Image path is required"):
            validator.validate(state={}, user=valid_user, image_path="")

    def test_nonexistent_file_raises(self, validator, valid_user):
        with pytest.raises(ValidationError, match="does not exist"):
            validator.validate(state={}, user=valid_user, image_path="/nonexistent/file.jpg")

    def test_directory_path_raises(self, validator, valid_user, tmp_dir):
        with pytest.raises(ValidationError, match="not a file"):
            validator.validate(state={}, user=valid_user, image_path=str(tmp_dir))

    def test_unsupported_extension_raises(self, validator, valid_user, tmp_dir):
        path = tmp_dir / "bad.bmp"
        path.write_bytes(b"\x00" * 100)
        with pytest.raises(ValidationError, match="Unsupported image format"):
            validator.validate(state={}, user=valid_user, image_path=str(path))

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png", ".webp"])
    def test_valid_extensions_accepted(self, validator, valid_user, tmp_dir, ext):
        path = tmp_dir / f"image{ext}"
        path.write_bytes(b"\x00" * 100)
        result = validator.validate(state={}, user=valid_user, image_path=str(path))
        assert result.image_path == str(path)

    def test_oversized_file_raises(self, validator, valid_user, tmp_dir):
        path = tmp_dir / "huge.jpg"
        path.write_bytes(b"\x00" * (25 * 1024 * 1024))
        with pytest.raises(ValidationError, match="too large"):
            validator.validate(state={}, user=valid_user, image_path=str(path))
