function execDaumPostcode() {
    new kakao.Postcode({
        oncomplete: function (data) {
            let roadAddr = data.roadAddress;
            let extraRoadAddr = "";

            if (data.bname !== "" && /[동|로|가]$/g.test(data.bname)) {
                extraRoadAddr += data.bname;
            }

            if (data.buildingName !== "" && data.apartment === "Y") {
                extraRoadAddr += (extraRoadAddr !== "" ? ", " + data.buildingName : data.buildingName);
            }

            if (extraRoadAddr !== "") {
                extraRoadAddr = " (" + extraRoadAddr + ")";
            }

            document.getElementById("postcode").value = data.zonecode;
            document.getElementById("roadAddress").value = roadAddr || "";
            document.getElementById("jibunAddress").value = data.jibunAddress || "";
            document.getElementById("extraAddress").value = extraRoadAddr;
            document.getElementById("detailAddress").focus();
        }
    }).open();
}

const useruseIdInput = document.getElementById("useruse_id");
const emailInput = document.getElementById("email");

const useruseIdMessage = document.getElementById("useruseIdMessage");
const emailMessage = document.getElementById("emailMessage");

const useruseIdChecked = document.getElementById("useruse_id_checked");
const emailChecked = document.getElementById("email_checked");

const checkedUseruseIdValue = document.getElementById("checked_useruse_id_value");
const checkedEmailValue = document.getElementById("checked_email_value");

function resetUseruseIdCheck() {
    useruseIdChecked.value = "false";
    checkedUseruseIdValue.value = "";
    useruseIdMessage.textContent = "";
    useruseIdMessage.className = "check-message";
}

function resetEmailCheck() {
    emailChecked.value = "false";
    checkedEmailValue.value = "";
    emailMessage.textContent = "";
    emailMessage.className = "check-message";
}

useruseIdInput.addEventListener("input", resetUseruseIdCheck);
emailInput.addEventListener("input", resetEmailCheck);

document.getElementById("checkUseruseIdBtn").addEventListener("click", async function () {
    const value = useruseIdInput.value.trim();

    if (!value) {
        alert("아이디를 입력해주세요.");
        useruseIdInput.focus();
        return;
    }

    try {
        const response = await fetch(`/api/check-duplicate?type=useruse_id&value=${encodeURIComponent(value)}`);
        const data = await response.json();

        useruseIdMessage.textContent = data.message;
        useruseIdMessage.className = data.available ? "check-message success" : "check-message error";

        if (data.available) {
            useruseIdChecked.value = "true";
            checkedUseruseIdValue.value = value;
        } else {
            useruseIdChecked.value = "false";
            checkedUseruseIdValue.value = "";
            useruseIdInput.focus();
        }
    } catch (error) {
        alert("아이디 중복 확인 중 오류가 발생했습니다.");
    }
});

document.getElementById("checkEmailBtn").addEventListener("click", async function () {
    const value = emailInput.value.trim();

    if (!value) {
        alert("이메일을 입력해주세요.");
        emailInput.focus();
        return;
    }

    try {
        const response = await fetch(`/api/check-duplicate?type=email&value=${encodeURIComponent(value)}`);
        const data = await response.json();

        emailMessage.textContent = data.message;
        emailMessage.className = data.available ? "check-message success" : "check-message error";

        if (data.available) {
            emailChecked.value = "true";
            checkedEmailValue.value = value;
        } else {
            emailChecked.value = "false";
            checkedEmailValue.value = "";
            emailInput.focus();
        }
    } catch (error) {
        alert("이메일 중복 확인 중 오류가 발생했습니다.");
    }
});

document.getElementById("signupForm").addEventListener("submit", function (e) {
    const currentUseruseId = useruseIdInput.value.trim();
    const currentEmail = emailInput.value.trim();

    if (useruseIdChecked.value !== "true" || checkedUseruseIdValue.value !== currentUseruseId) {
        e.preventDefault();
        alert("아이디 중복 확인을 해주세요.");
        useruseIdInput.focus();
        return;
    }

    if (emailChecked.value !== "true" || checkedEmailValue.value !== currentEmail) {
        e.preventDefault();
        alert("이메일 중복 확인을 해주세요.");
        emailInput.focus();
        return;
    }
});