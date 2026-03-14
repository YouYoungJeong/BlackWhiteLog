function confirmEdit() {
    return confirm("정말 수정하시겠습니까?");
}

function confirmDelete() {
    return confirm("정말 삭제하시겠습니까?");
}

// 이미지 처리
//  업로드 직후 브라우저에서 미리보기 보여주기 추가
document.addEventListener("DOMContentLoaded", function () {
    const imageInput = document.getElementById("menu-image-input");
    const previewImage = document.getElementById("previewImage");

    if (!imageInput || !previewImage) {
        return;
    }

    imageInput.addEventListener("change", function (event) {
        const file = event.target.files && event.target.files[0];

        if (!file) {
            previewImage.src = imageInput.dataset.defaultImage || previewImage.src;
            return;
        }

        const reader = new FileReader();

        reader.onload = function (loadEvent) {
            previewImage.src = loadEvent.target.result;
        };

        reader.readAsDataURL(file);
    });
});