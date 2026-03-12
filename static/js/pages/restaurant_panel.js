/************************************************************
 * 음식점 상세 패널 및 탭 로직 ####
 ************************************************************/
const detailPanel = document.getElementById("restaurantDetailPanel");
const closeDetailBtn = document.getElementById("closeDetailBtn");
const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanes = document.querySelectorAll(".tab-pane");

// 패널 닫기 이벤트
if (closeDetailBtn) {
    closeDetailBtn.addEventListener("click", () => {
        detailPanel.classList.add("hidden");
        resetReviewForm();
    });
}
// 지도 영역 클릭 시 패널 닫기
const mapArea = document.querySelector(".map-panel");
if (mapArea) {
    mapArea.addEventListener("click", (event) => {
        // 상세 패널 자체를 클릭했을 때는 안 닫히도록 예외 처리
        if (event.target.closest('#restaurantDetailPanel')) return;

        // 패널이 열려있을 때만 닫기
        if (!detailPanel.classList.contains("hidden")) {
            detailPanel.classList.add("hidden");
            resetReviewForm();
        }
    });
}

// 탭 전환 이벤트
tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        // 모든 탭 버튼과 내용 초기화
        tabButtons.forEach(b => b.classList.remove("active"));
        tabPanes.forEach(p => p.classList.add("hidden"));

        // 클릭된 탭 활성화
        btn.classList.add("active");
        const targetTabId = "tab-" + btn.getAttribute("data-tab");
        document.getElementById(targetTabId).classList.remove("hidden");
        // 만약 클릭한 탭이 'review(리뷰)' 탭이 아니라면 폼을 깨끗하게 청소합니다
        if (btn.getAttribute("data-tab") !== "review") {
            resetReviewForm();
        }
    });
});

// 패널 열기 및 AJAX 정보 호출 함수 
async function openDetailPanel(restaurantId) {
    const detailPanel = document.getElementById("restaurantDetailPanel");
    detailPanel.classList.remove("hidden");

    // 추가: 나중에 리뷰 저장할 때 쓰기 위해 ID를 저장해둡니다.
    detailPanel.setAttribute("data-id", restaurantId);
    
    // '정보' 탭을 강제로 클릭하여 활성화
    document.querySelector('.tab-btn[data-tab="info"]').click();

    const infoTab = document.getElementById("tab-info");
    infoTab.innerHTML = "<p>가게 정보를 불러오는 중...</p>";

    resetReviewForm();

    try {
        // Step 2: 서버에서 식당 상세 정보 가져오기
        const response = await fetch(`/api/restaurants/${restaurantId}`);
        if (!response.ok) throw new Error("정보를 불러오지 못했습니다.");
        const data = await response.json();

        // 1. 패널 상단 헤더 업데이트
        document.getElementById("detailRestaurantName").textContent = data.name;
        document.getElementById("detailMainImage").src = data.image_url || "https://dummyimage.com/400x200/e0e0e0/000000.png&text=No+Image";

        // 2. 정보 탭 내용 렌더링
        const isOpen = data.status === 'OPEN';
        infoTab.innerHTML = `
            <div style="line-height: 1.6;">
                <p><strong>📝 설명:</strong> ${data.description || '설명이 없습니다.'}</p>
                <p><strong>📞 전화:</strong> ${data.phone || '정보 없음'}</p>
                <p><strong>📍 주소:</strong> ${data.road_address || '정보 없음'}</p>
                <p><strong>⏰ 시간:</strong> ${data.business_hours || '정보 없음'}</p>
                <p><strong>운영:</strong> 
                    <span style="color: ${isOpen ? 'green' : 'red'}; font-weight: bold;">
                        ${isOpen ? '🟢 오픈중' : '🔴 영업종료'}
                    </span>
                </p>
            </div>
        `;

        // 3. [추가] 메뉴 탭 데이터 렌더링
        const menuTab = document.getElementById("tab-menu");
        menuTab.innerHTML = "<p>메뉴 정보를 불러오는 중...</p>";
        
        try {
            const menuRes = await fetch(`/api/restaurants/${restaurantId}/menus`);
            if (!menuRes.ok) throw new Error("메뉴 API 호출 실패");
            const menus = await menuRes.json();

            if (menus.length === 0) {
                menuTab.innerHTML = "<p style='color: var(--subtext);'>등록된 메뉴가 없습니다.</p>";
            } else {
                let menuHtml = '<ul style="list-style: none; padding: 0; margin: 0;">';
                menus.forEach(m => {
                    // 가격에 천 단위 콤마(,) 찍기
                    const priceFormatted = m.price.toLocaleString() + '원';
                    menuHtml += `
                        <li style="display: flex; justify-content: space-between; padding: 16px 0; border-bottom: 1px solid var(--line);">
                            <span style="font-weight: bold; color: var(--text);">${m.menu_name}</span>
                            <span style="color: var(--point-dark); font-weight: bold;">${priceFormatted}</span>
                        </li>
                    `;
                });
                menuHtml += '</ul>';
                menuTab.innerHTML = menuHtml;
            }
        } catch (menuError) {
            menuTab.innerHTML = `<p style="color:red;">메뉴를 불러오지 못했습니다.</p>`;
            console.error("Menu Fetch Error:", menuError);
        }

        // 4. [수정] 리뷰(댓글) 데이터 렌더링
        // 회원님이 만들어두신 'reviewListContainer'를 정확히 타겟팅합니다.
        const reviewContainer = document.getElementById("reviewListContainer");
        reviewContainer.innerHTML = "<p style='padding: 20px 0; text-align: center;'>리뷰를 불러오는 중...</p>";
        
        try {
            const reviewRes = await fetch(`/api/restaurants/${restaurantId}/reviews`);
            if (!reviewRes.ok) throw new Error("리뷰 API 호출 실패");
            const reviews = await reviewRes.json();

            if (reviews.length === 0) {
                // 리뷰가 없을 때
                reviewContainer.innerHTML = `
                    <div style="text-align: center; padding: 40px 0; color: #888;">
                        <p style="margin-bottom: 10px;">아직 작성된 리뷰가 없습니다.</p>
                        <p style="font-size: 0.9em;">첫 번째 리뷰의 주인공이 되어보세요!</p>
                    </div>
                `;
            } else {
                // 리뷰가 있을 때 리스트 생성
                let reviewHtml = '<ul style="list-style: none; padding: 0; margin: 0; margin-top: 10px;">';
                
                reviews.forEach(r => {
                    const dateStr = new Date(r.created_at).toLocaleDateString('ko-KR');
                    const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
                    const userImgStyle = r.user_image ? `background-image: url('${r.user_image}');` : `background-color: #ddd;`;
                    const reviewImageHtml = r.review_image ? `<img src="${r.review_image}" alt="리뷰 이미지" style="width: 100%; max-height: 200px; object-fit: cover; border-radius: 8px; margin-top: 12px;">` : '';
                    
                    let imageGalleryHtml = '';
                    if (r.review_images) {
                        // 콤마로 구분된 문자열을 배열로 변환
                        const imgList = r.review_images.split(','); 
                        imageGalleryHtml = `<div class="comment-image-gallery">`;
                        imgList.forEach(imgUrl => {
                            imageGalleryHtml += `<img src="${imgUrl}" class="comment-img-item" onclick="window.open('${imgUrl}')">`;
                        });
                        imageGalleryHtml += `</div>`;
                    }

                    reviewHtml += `
                            <li class="review-item-card">
                                <div class="review-user-info">
                                    <div class="user-profile-group">
                                        <div class="user-thumb" style="${userImgStyle}"></div>
                                        <span class="user-nickname">${r.nickname || '익명'}</span>
                                    </div>
                                    <span class="review-date">${dateStr}</span>
                                </div>
                                <div class="review-rating-stars">${stars}</div>
                                
                                ${imageGalleryHtml} 
                                <p class="review-text-content">${r.content}</p>
                                </li>
                        `;
                    });

                reviewHtml += '</ul>';
                reviewContainer.innerHTML = reviewHtml;
            }
        } catch (reviewError) {
            reviewContainer.innerHTML = `<p style="color:red; text-align:center;">리뷰를 불러오지 못했습니다.</p>`;
            console.error("Review Fetch Error:", reviewError);
        }

    } catch (error) {
        infoTab.innerHTML = `<p style="color:red;">오류 발생: ${error.message}</p>`;
        console.error("Detail Fetch Error:", error);
    }
}

document.addEventListener("click", (event) => {
    // 1. 클릭된 요소가 '.restaurant-card' 이거나 그 내부의 요소인지 확인합니다.
    const clickedCard = event.target.closest(".restaurant-card");
    
    // 2. 만약 식당 카드가 맞다면?
    if (clickedCard) {
        // html의 data-id 속성에서 식당 번호를 빼옵니다.
        const restaurantId = clickedCard.getAttribute("data-id");
        
        if (restaurantId) {
            openDetailPanel(restaurantId); // 패널 열기 함수 실행!
        }
    }
});

// =======================================================
// [수정] 리뷰 폼 별점 호버 & 클릭 애니메이션
// =======================================================
const starWrap = document.getElementById("starInputWrap");
const stars = document.querySelectorAll(".star-input-wrap .star");
const ratingInput = document.getElementById("reviewRating");
const reviewInputArea = document.getElementById("reviewInputArea");

if (starWrap && stars.length > 0) {
    // 별 색칠하는 공통 함수
    const updateStars = (value) => {
        stars.forEach(s => {
            if (parseInt(s.getAttribute("data-value")) <= value) {
                s.classList.add("active");
            } else {
                s.classList.remove("active");
            }
        });
    };

    stars.forEach(star => {
        // 1. 마우스 올릴 때 (Hover): 마우스 위치까지 별 채우기
        star.addEventListener("mouseenter", (e) => {
            updateStars(parseInt(e.target.getAttribute("data-value")));
        });

        // 2. 클릭했을 때 (Click): 점수 확정 & 입력창 열기
        star.addEventListener("click", (e) => {
            const clickedValue = parseInt(e.target.getAttribute("data-value"));
            starWrap.setAttribute("data-current-rating", clickedValue); // 확정 점수 기록
            ratingInput.value = clickedValue;
            updateStars(clickedValue);
            
            // 숨겨져 있던 리뷰 입력창 스르륵 등장!
            reviewInputArea.classList.remove("hidden");
        });
    });

    // 3. 마우스가 별 영역을 벗어날 때 (Leave): 클릭해서 확정된 점수로 되돌리기
    starWrap.addEventListener("mouseleave", () => {
        const currentRating = parseInt(starWrap.getAttribute("data-current-rating") || "0");
        updateStars(currentRating);
    });
}

// [추가] 리뷰 폼을 초기 상태로 되돌리는 청소 함수
function resetReviewForm() {
    const starWrapReset = document.getElementById("starInputWrap");
    if (starWrapReset) {
        starWrapReset.setAttribute("data-current-rating", "0");
        document.getElementById("reviewRating").value = "0";
        document.getElementById("reviewContent").value = "";
        document.getElementById("reviewImage").value = "";
        
        // 추가: 미리보기 영역 초기화
        dataTransfer = new DataTransfer(); 
        if (reviewImageInput) reviewImageInput.value = "";
        if (previewContainer) previewContainer.classList.add("hidden");
        if (previewSlider) previewSlider.innerHTML = "";
        
        // 텍스트 입력창 다시 숨기기
        const inputArea = document.getElementById("reviewInputArea");
        if (inputArea) inputArea.classList.add("hidden"); 
        
        // 노란 별 초기화
        document.querySelectorAll(".star-input-wrap .star").forEach(s => s.classList.remove("active"));
    }
}

// =======================================================
// [업그레이드] 이미지 개별 삭제가 가능한 멀티 미리보기
// =======================================================
const reviewImageInput = document.getElementById("reviewImage");
const previewContainer = document.getElementById("imagePreviewContainer");
const previewSlider = document.getElementById("previewSlider");

// 현재 선택된 파일들을 관리할 전역 변수 역할을 할 DataTransfer 객체
let dataTransfer = new DataTransfer();

if (reviewImageInput && previewSlider) {
    // 1. 파일 선택 시 실행
    reviewImageInput.addEventListener("change", function() {
        // 새로 선택한 파일들을 기존 DataTransfer에 추가 (누적 선택 가능)
        const files = Array.from(this.files);
        
        files.forEach(file => dataTransfer.items.add(file));
        
        // input의 파일 목록을 DataTransfer의 내용으로 동기화
        this.files = dataTransfer.files;
        
        renderPreviews();
    });

    // 2. 미리보기 렌더링 함수
    function renderPreviews() {
        previewSlider.innerHTML = "";
        const files = Array.from(dataTransfer.files);

        if (files.length > 0) {
            previewContainer.classList.remove("hidden");
            files.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const div = document.createElement("div");
                    div.className = "preview-item";
                    div.innerHTML = `
                        <img src="${e.target.result}">
                        <button type="button" class="remove-img-btn" data-index="${index}">×</button>
                    `;
                    previewSlider.appendChild(div);
                };
                reader.readAsDataURL(file);
            });
        } else {
            previewContainer.classList.add("hidden");
        }
    }

    // 3. 개별 삭제 클릭 이벤트 (이벤트 위임)
    previewSlider.addEventListener("click", (e) => {
        e.stopPropagation(); // 패널 닫힘 방지

        if (e.target.classList.contains("remove-img-btn")) {
            const indexToRemove = parseInt(e.target.getAttribute("data-index"));
            
            // 새로운 DataTransfer 객체를 만들어 삭제할 인덱스만 제외하고 다시 담기
            const newDataTransfer = new DataTransfer();
            const files = Array.from(dataTransfer.files);
            
            files.forEach((file, i) => {
                if (i !== indexToRemove) {
                    newDataTransfer.items.add(file);
                }
            });

            // 원본 객체 교체 및 input 동기화
            dataTransfer = newDataTransfer;
            reviewImageInput.files = dataTransfer.files;

            // 다시 그리기
            renderPreviews();
        }
    });
}

// =======================================================
// [신규] Step 4-4: 리뷰 서버 전송 (이미지 포함)
// =======================================================
document.getElementById("submitReviewBtn").addEventListener("click", async () => {
    const detailPanel = document.getElementById("restaurantDetailPanel");
    const restaurantId = detailPanel.getAttribute("data-id");
    const rating = document.getElementById("reviewRating").value;
    const content = document.getElementById("reviewContent").value;

    // 유효성 검사
    if (rating === "0") return alert("별점을 선택해주세요!");
    if (!content.trim()) return alert("리뷰 내용을 입력해주세요!");

    // 파일 전송을 위한 FormData 객체 생성
    const formData = new FormData();
    formData.append("rating", rating);
    formData.append("content", content);
    
    // dataTransfer에 담긴 '개별 삭제 반영된' 파일들을 모두 추가
    const files = dataTransfer.files;
    for (let i = 0; i < files.length; i++) {
        formData.append("images", files[i]);
    }

    try {
        const response = await fetch(`/api/restaurants/${restaurantId}/reviews`, {
            method: "POST",
            body: formData // Content-Type은 브라우저가 자동으로 설정하므로 생략합니다.
        });

        const result = await response.json();

        if (result.success) {
            alert("리뷰가 등록되었습니다!");
            resetReviewForm(); // 폼 초기화
            openDetailPanel(restaurantId); // 리뷰 목록 새로고침하여 방금 쓴 글 확인
        } else {
            alert("등록 실패: " + result.message);
        }
    } catch (error) {
        console.error("Save Review Error:", error);
        alert("서버 통신 중 오류가 발생했습니다.");
    }
});