// =========================
// 관리자 리뷰 댓글 삭제 전용 JS
// 파일명: static/js/admin_review_comment.js
// 설명:
// - 댓글 삭제 버튼 클릭 감지
// - 관리자 삭제 API 호출
// - 성공 시 화면에서 댓글 제거
// =========================
const AdminReviewComment = (() => {
    // 댓글 삭제 API 호출
    async function deleteComment(commentId) {
        const response = await fetch(`/admin/review-comments/delete/${commentId}`, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const contentType = response.headers.get("content-type") || "";

        // JSON 응답이 아닐 수도 있으니 방어 처리
        if (!contentType.includes("application/json")) {
            throw new Error("서버 응답 형식이 올바르지 않습니다.");
        }

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "댓글 삭제에 실패했습니다.");
        }

        return data;
    }

    // 클릭 이벤트 처리
    async function handleDeleteClick(event) {
        const deleteButton = event.target.closest(".js-comment-delete-btn");
        if (!deleteButton) return;

        event.preventDefault();

        const commentId = deleteButton.dataset.commentId;
        if (!commentId) {
            alert("댓글 번호를 찾을 수 없습니다.");
            return;
        }

        const isConfirmed = confirm("이 댓글을 삭제하시겠습니까?");
        if (!isConfirmed) return;

        // 중복 클릭 방지
        deleteButton.disabled = true;

        try {
            await deleteComment(commentId);

            const commentItem = deleteButton.closest(".comment-item");
            if (commentItem) {
                commentItem.remove();
            } else {
                // 혹시 구조가 다르면 새로고침
                window.location.reload();
            }

            alert("댓글이 삭제되었습니다.");
        } catch (error) {
            alert(error.message || "댓글 삭제 중 오류가 발생했습니다.");
            deleteButton.disabled = false;
        }
    }

    // 초기화
    function init() {
        document.addEventListener("click", handleDeleteClick);
    }

    return {
        init
    };
})();

// 페이지 로드 후 실행
document.addEventListener("DOMContentLoaded", () => {
    AdminReviewComment.init();
});