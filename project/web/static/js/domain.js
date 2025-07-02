// 도메인 형식 검증
function validateDomain(domain) {
    // 도메인 정규식 패턴
    const pattern = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
    return pattern.test(domain);
}

// 폼 검증
function validateForm(form) {
    const domain = form.domain.value.trim();
    const description = form.description.value.trim();
    
    if (!domain) {
        alert('도메인을 입력해주세요.');
        form.domain.focus();
        return false;
    }
    
    if (!validateDomain(domain)) {
        alert('올바른 도메인 형식이 아닙니다.\n예: example.com');
        form.domain.focus();
        return false;
    }
    
    if (description.length > 255) {
        alert('설명은 255자를 초과할 수 없습니다.');
        form.description.focus();
        return false;
    }
    
    return true;
}

// 정렬 상태를 저장할 변수
let currentSort = { column: -1, ascending: true };

// 테이블 정렬 함수
function sortTable(columnIndex) {
    const tbody = document.getElementById('domainTableBody');
    const rows = Array.from(tbody.getElementsByTagName('tr'));
    const headers = document.querySelectorAll('th');
    
    // 이전 정렬 아이콘 초기화
    headers.forEach(header => {
        const icon = header.querySelector('i');
        if (icon) {
            icon.className = 'bi bi-arrow-down-up';
        }
    });

    // 같은 열을 다시 클릭하면 정렬 방향 변경
    if (currentSort.column === columnIndex) {
        currentSort.ascending = !currentSort.ascending;
    } else {
        currentSort.column = columnIndex;
        currentSort.ascending = true;
    }

    // 정렬 아이콘 업데이트
    const currentHeader = headers[columnIndex];
    const icon = currentHeader.querySelector('i');
    if (icon) {
        icon.className = `bi bi-arrow-${currentSort.ascending ? 'up' : 'down'}`;
    }

    rows.sort((a, b) => {
        let aValue, bValue;
        
        // 상태 열
        if (columnIndex === 0) {
            aValue = a.querySelector('span').textContent;
            bValue = b.querySelector('span').textContent;
        }
        // 날짜 열
        else if (columnIndex === 3) {
            const aInput = a.querySelector('.domain-timestamp');
            const bInput = b.querySelector('.domain-timestamp');
            const aDate = new Date(aInput ? aInput.value : a.cells[columnIndex].textContent.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
            const bDate = new Date(bInput ? bInput.value : b.cells[columnIndex].textContent.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
            
            return currentSort.ascending ? aDate - bDate : bDate - aDate;
        }
        // 다른 열들
        else {
            const aCell = a.getElementsByTagName('td')[columnIndex];
            const bCell = b.getElementsByTagName('td')[columnIndex];
            aValue = aCell.dataset.domain || aCell.dataset.description || aCell.textContent;
            bValue = bCell.dataset.domain || bCell.dataset.description || bCell.textContent;
        }

        // 정렬 방향에 따라 비교
        const compareResult = aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
        return currentSort.ascending ? compareResult : -compareResult;
    });

    // 정렬된 행들을 다시 테이블에 추가
    rows.forEach(row => tbody.appendChild(row));
}

// 테이블 헤더에 클릭 이벤트 리스너 추가
document.addEventListener('DOMContentLoaded', () => {
    const headers = document.querySelectorAll('th');
    headers.forEach((header, index) => {
        if (index < headers.length - 1) { // 작업 열 제외
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => sortTable(index));
        }
    });
    
    loadDomains();
});

// 도메인 목록 로드
async function loadDomains() {
    try {
        const response = await fetch('/api/domains');
        const data = await response.json();
        if (data.status === 'success') {
            const tbody = document.getElementById('domainTableBody');
            tbody.innerHTML = '';
            data.data.forEach(domain => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <span class="badge status-badge ${domain.list_type === 'allow' ? 'bg-success' : 'bg-danger'}">
                            ${domain.list_type === 'allow' ? '허용' : '차단'}
                        </span>
                        ${!domain.is_active ? '<span class="badge bg-warning ms-1">비활성화</span>' : ''}
                    </td>
                    <td data-domain="${domain.domain}">${domain.domain}</td>
                    <td data-description="${domain.description || ''}">${domain.description || ''}</td>
                    <td data-timestamp="${domain.updated_at}">${new Date(domain.updated_at).toLocaleString('ko-KR')}</td>
                    <td class="action-buttons">
                        <input type="hidden" class="domain-type" value="${domain.list_type}">
                        <input type="hidden" class="domain-name" value="${domain.domain}">
                        <input type="hidden" class="domain-description" value="${domain.description || ''}">
                        <input type="hidden" class="domain-timestamp" value="${domain.updated_at}">
                        <input type="hidden" class="domain-active" value="${domain.is_active}">
                        <button class="btn btn-sm btn-outline-primary" onclick="editDomain(${domain.idx}, this)">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm ${domain.is_active ? 'btn-outline-warning' : 'btn-outline-success'}" onclick="toggleActive(${domain.idx}, ${domain.is_active})">
                            <i class="bi ${domain.is_active ? 'bi-pause-fill' : 'bi-play-fill'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteDomain(${domain.idx})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // 정렬이 적용되어 있다면 다시 적용
            if (currentSort.column !== -1) {
                sortTable(currentSort.column);
            }
        }
    } catch (error) {
        console.error('도메인 로드 실패:', error);
        alert('도메인 목록을 불러오는데 실패했습니다.');
    }
}

// 도메인 추가
async function addDomain() {
    const form = document.getElementById('addDomainForm');
    const formData = new FormData(form);
    
    try {
        const response = await fetch('/api/domains', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('addDomainModal')).hide();
            form.reset();
            loadDomains();
        } else {
            alert(data.message || '도메인 추가에 실패했습니다.');
        }
    } catch (error) {
        console.error('도메인 추가 실패:', error);
        alert('도메인 추가에 실패했습니다.');
    }
}

// 도메인 수정 모달 열기
function editDomain(idx, button) {
    const form = document.getElementById('editDomainForm');
    form.idx.value = idx;
    form.list_type.value = button.parentElement.querySelector('.domain-type').value;
    form.domain.value = button.parentElement.querySelector('.domain-name').value;
    form.description.value = button.parentElement.querySelector('.domain-description').value;
    
    const modal = new bootstrap.Modal(document.getElementById('editDomainModal'));
    modal.show();
}

// 도메인 수정
async function updateDomain() {
    const form = document.getElementById('editDomainForm');
    const formData = new FormData(form);
    const idx = form.idx.value;
    
    try {
        const response = await fetch(`/api/domains/${idx}`, {
            method: 'PUT',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('editDomainModal')).hide();
            loadDomains();
        } else {
            alert(data.message || '도메인 수정에 실패했습니다.');
        }
    } catch (error) {
        console.error('도메인 수정 실패:', error);
        alert('도메인 수정에 실패했습니다.');
    }
}

// 도메인 삭제
async function deleteDomain(idx) {
    if (!confirm('정말 이 도메인을 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/domains/${idx}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadDomains();
        } else {
            alert(data.message || '도메인 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('도메인 삭제 실패:', error);
        alert('도메인 삭제에 실패했습니다.');
    }
}

// 도메인 활성화/비활성화 토글
async function toggleActive(idx, currentActive) {
    const action = currentActive ? '비활성화' : '활성화';
    if (!confirm(`정말 이 도메인을 ${action} 하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/domains/${idx}/toggle`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_active: !currentActive
            })
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadDomains();
        } else {
            alert(data.message || `도메인 ${action}에 실패했습니다.`);
        }
    } catch (error) {
        console.error(`도메인 ${action} 실패:`, error);
        alert(`도메인 ${action}에 실패했습니다.`);
    }
} 