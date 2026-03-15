document.addEventListener("DOMContentLoaded", () => {
    // ==================================================================================
    // 공지사항 관리 JS 요약
    // ----------------------------------------------------------------------------------
    // 1. 식당 선택 시 해당 restaurant_id 기준으로 목록을 다시 조회한다.
    // 2. 공지 등록/수정 시 FormData 로 제목/내용/이미지/상단고정을 전송한다.
    // 3. 이미지 미리보기는 기본 공백 상태이고, 파일 선택 시에만 표시된다.
    // 4. 수정 클릭 시 상세 조회 후 폼에 값을 다시 채운다.
    // 5. 삭제 클릭 시 DB 삭제 후 목록을 다시 렌더링한다.
    // ==================================================================================

    // -------------------------------------------------------------------------
    // 공지사항 등록/수정 폼 관련 요소
    // -------------------------------------------------------------------------
    const noticeForm = document.getElementById("noticeForm");
    const restaurantSelect = document.getElementById("restaurant-id");
    const noticeIdInput = document.getElementById("notice-id");
    const noticeTitleInput = document.getElementById("notice-title");
    const noticeContentInput = document.getElementById("notice-content");
    const noticePinInput = document.getElementById("notice-pin");
    const noticeFileInput = document.getElementById("notice-file");
    const currentPageInput = document.getElementById("current-page");
    const removeImageInput = document.getElementById("remove-image");

    // -------------------------------------------------------------------------
    // 공지사항 목록/페이징 관련 요소
    // -------------------------------------------------------------------------
    const noticeList = document.getElementById("noticeList");
    const totalNoticeCount = document.getElementById("totalNoticeCount");
    const pageStatus = document.getElementById("pageStatus");
    const prevPageBtn = document.getElementById("prevPageBtn");
    const nextPageBtn = document.getElementById("nextPageBtn");

    // -------------------------------------------------------------------------
    // 폼 제어 버튼 / 이미지 미리보기 요소
    // -------------------------------------------------------------------------
    const resetFormBtn = document.getElementById("resetFormBtn");
    const removeImageBtn = document.getElementById("removeImageBtn");
    const noticeImagePreview = document.getElementById("noticeImagePreview");

    // -------------------------------------------------------------------------
    // 현재 페이지 / 전체 페이지 초기값
    // - 서버에서 렌더링한 초기 payload 값을 우선 사용한다.
    // -------------------------------------------------------------------------
    let currentPage = Number(window.ownerNoticeInitialData?.initial_payload?.current_page || 1);
    let totalPages = Number(window.ownerNoticeInitialData?.initial_payload?.total_pages || 1);

    // -------------------------------------------------------------------------
    // 이미지 미리보기 처리
    // - src 값이 있으면 이미지 표시
    // - 없으면 빈 공백 상태(hidden)로 처리
    // -------------------------------------------------------------------------
    function setImagePreview(src) {
        if (src) {
            noticeImagePreview.src = src;
            noticeImagePreview.hidden = false;
        } else {
            noticeImagePreview.src = "";
            noticeImagePreview.hidden = true;
        }
    }

    // -------------------------------------------------------------------------
    // 폼 초기화
    // - 선택된 식당은 유지
    // - notice_id 초기화로 신규 등록 모드 전환
    // - 이미지 삭제 여부 기본값 N
    // - 현재 페이지 유지
    // - 이미지 미리보기 비우기
    // -------------------------------------------------------------------------
    function resetForm() {
        const selectedRestaurantId = restaurantSelect.value;

        noticeForm.reset();
        restaurantSelect.value = selectedRestaurantId;
        noticeIdInput.value = "";
        removeImageInput.value = "N";
        currentPageInput.value = String(currentPage);
        setImagePreview("");
    }

    // -------------------------------------------------------------------------
    // 페이징 UI 렌더링
    // - current_page / total_pages / 이전/다음 버튼 상태 갱신
    // -------------------------------------------------------------------------
    function renderPagination(payload) {
        currentPage = Number(payload.current_page || 1);
        totalPages = Number(payload.total_pages || 1);

        currentPageInput.value = String(currentPage);
        pageStatus.textContent = `${currentPage} / ${totalPages}`;

        prevPageBtn.disabled = !payload.has_prev;
        nextPageBtn.disabled = !payload.has_next;
    }

    // -------------------------------------------------------------------------
    // XSS 방지를 위한 HTML 이스케이프 처리
    // - 목록 렌더링 시 사용자 입력값을 그대로 넣지 않도록 변환
    // -------------------------------------------------------------------------
    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    // -------------------------------------------------------------------------
    // 공지 목록 렌더링
    // - 공지 목록이 없으면 empty-state 출력
    // - 있으면 카드 목록 HTML 생성
    // -------------------------------------------------------------------------
    function renderNoticeList(payload) {
        totalNoticeCount.textContent = payload.total_notice_count || 0;

        if (!payload.notice_list || payload.notice_list.length === 0) {
            noticeList.innerHTML = `
                <article class="notice-item empty-state">
                    <div class="empty-icon">📢</div>
                    <strong>등록된 공지사항이 없습니다.</strong>
                    <p>이벤트, 휴무, 운영시간 변경 등 중요한 내용을 작성해보세요.</p>
                </article>
            `;
            renderPagination(payload);
            return;
        }

        noticeList.innerHTML = payload.notice_list.map((notice) => {
            const pinnedHtml = Number(notice.is_pinned) === 1
                ? `<strong class="notice-badge">고정</strong>`
                : "";

            const thumbHtml = notice.thumb_url
                ? `
                    <div class="notice-thumb-wrap">
                        <img src="/static/${notice.thumb_url}" alt="공지 썸네일" class="notice-thumb" />
                    </div>
                  `
                : "";

            return `
                <article class="notice-item" data-notice-id="${notice.notice_id}">
                    <div class="notice-item-top">
                        <div class="notice-top-left">
                            ${pinnedHtml}
                            <span class="notice-date">${escapeHtml(notice.created_at)}</span>
                        </div>
                    </div>

                    <div class="notice-item-body">
                        <div class="notice-item-text">
                            <h3>${escapeHtml(notice.notice_title)}</h3>
                            <p>${escapeHtml(notice.notice_content)}</p>
                        </div>
                        ${thumbHtml}
                    </div>

                    <div class="notice-item-actions">
                        <button type="button" class="text-btn notice-edit-btn" data-notice-id="${notice.notice_id}">수정</button>
                        <button type="button" class="text-btn danger notice-delete-btn" data-notice-id="${notice.notice_id}">삭제</button>
                    </div>
                </article>
            `;
        }).join("");

        renderPagination(payload);
    }

    // -------------------------------------------------------------------------
    // 공지 목록 비동기 조회
    // - 선택된 식당 + 페이지 기준으로 목록 API 호출
    // -------------------------------------------------------------------------
    async function loadNoticeList(page = 1) {
        const restaurantId = restaurantSelect.value;

        const response = await fetch(`/owner/notice_management/api/list?restaurant_id=${encodeURIComponent(restaurantId)}&page=${encodeURIComponent(page)}`);
        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 목록을 불러오지 못했습니다.");
            return;
        }

        renderNoticeList(result);
    }

    // -------------------------------------------------------------------------
    // 공지 상세 조회
    // - 수정 버튼 클릭 시 해당 공지 1건의 데이터를 받아와 폼에 채운다.
    // - 기존 이미지가 있으면 미리보기 표시
    // -------------------------------------------------------------------------
    async function loadNoticeDetail(noticeId) {
        const restaurantId = restaurantSelect.value;

        const response = await fetch(`/owner/notice_management/api/detail/${noticeId}?restaurant_id=${encodeURIComponent(restaurantId)}`);
        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 상세 정보를 불러오지 못했습니다.");
            return;
        }

        noticeIdInput.value = result.notice_id || "";
        noticeTitleInput.value = result.notice_title || "";
        noticeContentInput.value = result.notice_content || "";
        noticePinInput.checked = Number(result.is_pinned) === 1;
        removeImageInput.value = "N";

        if (result.notice_url) {
            setImagePreview(`/static/${result.notice_url}`);
        } else {
            setImagePreview("");
        }

        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // -------------------------------------------------------------------------
    // 공지 저장
    // - 신규 등록: client_notice_id 없음
    // - 수정 저장: client_notice_id 있음
    // - 이미지 파일이 있으면 FormData 에 함께 담아 전송
    // -------------------------------------------------------------------------
    async function saveNotice(event) {
        event.preventDefault();

        const formData = new FormData();
        formData.append("client_notice_id", noticeIdInput.value.trim());
        formData.append("client_restaurant_id", restaurantSelect.value);
        formData.append("client_notice_title", noticeTitleInput.value.trim());
        formData.append("client_notice_content", noticeContentInput.value.trim());
        formData.append("client_is_pinned", noticePinInput.checked ? "Y" : "N");
        formData.append("client_remove_image", removeImageInput.value);
        formData.append("client_page", currentPageInput.value || "1");

        if (noticeFileInput.files[0]) {
            formData.append("client_notice_image", noticeFileInput.files[0]);
        }

        const response = await fetch("/owner/notice_management/api/save", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 저장에 실패했습니다.");
            return;
        }

        alert(result.message || "저장되었습니다.");
        renderNoticeList(result);
        resetForm();
    }

    // -------------------------------------------------------------------------
    // 공지 삭제
    // - 현재 선택된 식당 / 현재 페이지 정보를 함께 전달
    // - 삭제 후 목록을 다시 렌더링
    // -------------------------------------------------------------------------
    async function deleteNotice(noticeId) {
        const formData = new FormData();
        formData.append("client_restaurant_id", restaurantSelect.value);
        formData.append("client_page", currentPageInput.value || "1");

        const response = await fetch(`/owner/notice_management/api/delete/${noticeId}`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 삭제에 실패했습니다.");
            return;
        }

        alert(result.message || "삭제되었습니다.");
        renderNoticeList(result);
        resetForm();
    }

    // -------------------------------------------------------------------------
    // 식당 변경 이벤트
    // - 식당이 바뀌면 페이지를 1로 초기화하고 목록 재조회
    // -------------------------------------------------------------------------
    restaurantSelect.addEventListener("change", async () => {
        currentPage = 1;
        currentPageInput.value = "1";
        resetForm();
        await loadNoticeList(1);
    });

    // -------------------------------------------------------------------------
    // 파일 선택 시 미리보기 처리
    // - 선택한 파일을 object URL 로 미리보기 표시
    // - 이미지 삭제 여부를 N 으로 되돌림
    // -------------------------------------------------------------------------
    noticeFileInput.addEventListener("change", () => {
        const file = noticeFileInput.files[0];

        if (!file) {
            setImagePreview("");
            return;
        }

        const previewUrl = URL.createObjectURL(file);
        setImagePreview(previewUrl);
        removeImageInput.value = "N";
    });

    // -------------------------------------------------------------------------
    // 이미지 제거 버튼
    // - 파일 input 비우기
    // - 서버에 기존 이미지 삭제 의도를 전달하기 위해 Y 저장
    // - 미리보기 제거
    // -------------------------------------------------------------------------
    removeImageBtn.addEventListener("click", () => {
        noticeFileInput.value = "";
        removeImageInput.value = "Y";
        setImagePreview("");
    });

    // -------------------------------------------------------------------------
    // 취소 버튼
    // - 현재 식당/페이지는 유지하면서 폼만 초기화
    // -------------------------------------------------------------------------
    resetFormBtn.addEventListener("click", () => {
        resetForm();
    });

    // -------------------------------------------------------------------------
    // 이전 페이지 버튼
    // -------------------------------------------------------------------------
    prevPageBtn.addEventListener("click", async () => {
        if (currentPage > 1) {
            await loadNoticeList(currentPage - 1);
        }
    });

    // -------------------------------------------------------------------------
    // 다음 페이지 버튼
    // -------------------------------------------------------------------------
    nextPageBtn.addEventListener("click", async () => {
        if (currentPage < totalPages) {
            await loadNoticeList(currentPage + 1);
        }
    });

    // -------------------------------------------------------------------------
    // 목록 내 수정/삭제 버튼 이벤트 위임
    // - 수정: 상세 조회 후 폼 채우기
    // - 삭제: 확인창 후 삭제 API 호출
    // -------------------------------------------------------------------------
    noticeList.addEventListener("click", async (event) => {
        const editBtn = event.target.closest(".notice-edit-btn");
        const deleteBtn = event.target.closest(".notice-delete-btn");

        if (editBtn) {
            const noticeId = editBtn.dataset.noticeId;
            await loadNoticeDetail(noticeId);
            return;
        }

        if (deleteBtn) {
            const noticeId = deleteBtn.dataset.noticeId;
            const isConfirmed = window.confirm("해당 공지사항을 삭제하시겠습니까?");

            if (isConfirmed) {
                await deleteNotice(noticeId);
            }
        }
    });

    // -------------------------------------------------------------------------
    // 폼 submit 이벤트 연결
    // -------------------------------------------------------------------------
    noticeForm.addEventListener("submit", saveNotice);

    // -------------------------------------------------------------------------
    // 최초 페이지 진입 시 서버가 내려준 초기 payload 기준으로 페이징 상태 표시
    // -------------------------------------------------------------------------
    renderPagination(window.ownerNoticeInitialData?.initial_payload || {
        current_page: 1,
        total_pages: 1,
        has_prev: false,
        has_next: false
    });
});