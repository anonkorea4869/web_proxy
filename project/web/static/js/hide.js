// 숨김 도메인 목록 로드
async function loadHides() {
    try {
        const response = await fetch('/api/hides');
        const data = await response.json();
        if (data.status === 'success') {
            const tbody = document.getElementById('hideTableBody');
            tbody.innerHTML = '';
            data.data.forEach(hide => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <span class="badge status-badge badge-success">성공</span>
                        ${!hide.is_active ? '<span class="badge bg-warning ms-1">비활성화</span>' : ''}
                    </td>
                    <td data-domain="${hide.domain}">${hide.domain}</td>
                    <td data-description="${hide.description || ''}">${hide.description || ''}</td>
                    <td data-timestamp="${hide.updated_at}">${new Date(hide.updated_at).toLocaleString('ko-KR')}</td>
                    <td class="action-buttons">
                        <input type="hidden" class="hide-domain" value="${hide.domain}">
                        <input type="hidden" class="hide-description" value="${hide.description || ''}">
                        <input type="hidden" class="hide-timestamp" value="${hide.updated_at}">
                        <input type="hidden" class="hide-active" value="${hide.is_active}">
                        <button class="btn btn-sm btn-outline-primary" onclick="editHide(${hide.idx}, this)">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm ${hide.is_active ? 'btn-outline-warning' : 'btn-outline-success'}" onclick="toggleActive(${hide.idx}, ${hide.is_active})">
                            <i class="bi ${hide.is_active ? 'bi-pause-fill' : 'bi-play-fill'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteHide(${hide.idx})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (error) {
        console.error('숨김 도메인 로드 실패:', error);
        alert('숨김 도메인 목록을 불러오는데 실패했습니다.');
    }
}

// 숨김 도메인 추가
async function addHide() {
    const form = document.getElementById('addHideForm');
    const formData = new FormData(form);
    
    try {
        const response = await fetch('/api/hides', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('addHideModal')).hide();
            form.reset();
            loadHides();
        } else {
            alert(data.message || '숨김 도메인 추가에 실패했습니다.');
        }
    } catch (error) {
        console.error('숨김 도메인 추가 실패:', error);
        alert('숨김 도메인 추가에 실패했습니다.');
    }
}

// 숨김 도메인 수정 모달 열기
function editHide(idx, button) {
    const form = document.getElementById('editHideForm');
    form.idx.value = idx;
    form.domain.value = button.parentElement.querySelector('.hide-domain').value;
    form.description.value = button.parentElement.querySelector('.hide-description').value;
    form.is_active.checked = button.parentElement.querySelector('.hide-active').value === 'true';
    
    const modal = new bootstrap.Modal(document.getElementById('editHideModal'));
    modal.show();
}

// 숨김 도메인 수정
async function updateHide() {
    const form = document.getElementById('editHideForm');
    const formData = new FormData(form);
    const idx = form.idx.value;
    
    try {
        const response = await fetch(`/api/hides/${idx}`, {
            method: 'PUT',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('editHideModal')).hide();
            loadHides();
        } else {
            alert(data.message || '숨김 도메인 수정에 실패했습니다.');
        }
    } catch (error) {
        console.error('숨김 도메인 수정 실패:', error);
        alert('숨김 도메인 수정에 실패했습니다.');
    }
}

// 숨김 도메인 삭제
async function deleteHide(idx) {
    if (!confirm('정말 이 숨김 도메인을 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/hides/${idx}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadHides();
        } else {
            alert(data.message || '숨김 도메인 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('숨김 도메인 삭제 실패:', error);
        alert('숨김 도메인 삭제에 실패했습니다.');
    }
}

// 숨김 도메인 활성화/비활성화 토글
async function toggleActive(idx, currentActive) {
    const action = currentActive ? '비활성화' : '활성화';
    if (!confirm(`정말 이 숨김 도메인을 ${action} 하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/hides/${idx}/toggle`, {
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
            loadHides();
        } else {
            alert(data.message || `숨김 도메인 ${action}에 실패했습니다.`);
        }
    } catch (error) {
        console.error(`숨김 도메인 ${action} 실패:`, error);
        alert(`숨김 도메인 ${action}에 실패했습니다.`);
    }
}

// 정렬 상태를 저장할 변수
let currentSort = { column: -1, ascending: true };

// 테이블 정렬 함수
function sortTable(columnIndex) {
    const tbody = document.getElementById('hideTableBody');
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
            const aInput = a.querySelector('.hide-timestamp');
            const bInput = b.querySelector('.hide-timestamp');
            const aDate = new Date(aInput ? aInput.value : a.cells[columnIndex].textContent.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
            const bDate = new Date(bInput ? bInput.value : b.cells[columnIndex].textContent.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
            
            return currentSort.ascending ? aDate - bDate : bDate - aDate;
        }
        // 다른 열들
        else {
            const aCell = a.getElementsByTagName('td')[columnIndex];
            const bCell = b.getElementsByTagName('td')[columnIndex];
            aValue = aCell.textContent;
            bValue = bCell.textContent;
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
    
    loadHides();
}); 