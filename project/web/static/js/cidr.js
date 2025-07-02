// CIDR 목록 로드
async function loadCidrs() {
    try {
        const response = await fetch('/api/cidrs');
        const data = await response.json();
        if (data.status === 'success') {
            const tbody = document.getElementById('cidrTableBody');
            tbody.innerHTML = '';
            data.data.forEach(cidr => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <span class="badge status-badge ${cidr.list_type === 'allow' ? 'bg-success' : 'bg-danger'}">
                            ${cidr.list_type === 'allow' ? '허용' : '차단'}
                        </span>
                        ${!cidr.is_active ? '<span class="badge bg-warning ms-1">비활성화</span>' : ''}
                    </td>
                    <td data-cidr="${cidr.cidr}">${cidr.cidr}</td>
                    <td data-description="${cidr.description || ''}">${cidr.description || ''}</td>
                    <td data-timestamp="${cidr.updated_at}">${new Date(cidr.updated_at).toLocaleString('ko-KR')}</td>
                    <td class="action-buttons">
                        <input type="hidden" class="cidr-type" value="${cidr.list_type}">
                        <input type="hidden" class="cidr-value" value="${cidr.cidr}">
                        <input type="hidden" class="cidr-description" value="${cidr.description || ''}">
                        <input type="hidden" class="cidr-timestamp" value="${cidr.updated_at}">
                        <input type="hidden" class="cidr-active" value="${cidr.is_active}">
                        <button class="btn btn-sm btn-outline-primary" onclick="editCidr(${cidr.idx}, this)">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm ${cidr.is_active ? 'btn-outline-warning' : 'btn-outline-success'}" onclick="toggleActive(${cidr.idx}, ${cidr.is_active})">
                            <i class="bi ${cidr.is_active ? 'bi-pause-fill' : 'bi-play-fill'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteCidr(${cidr.idx})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (error) {
        console.error('CIDR 로드 실패:', error);
        alert('CIDR 목록을 불러오는데 실패했습니다.');
    }
}

// CIDR 추가
async function addCidr() {
    const form = document.getElementById('addCidrForm');
    const formData = new FormData(form);
    
    try {
        const response = await fetch('/api/cidrs', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('addCidrModal')).hide();
            form.reset();
            loadCidrs();
        } else {
            alert(data.message || 'CIDR 추가에 실패했습니다.');
        }
    } catch (error) {
        console.error('CIDR 추가 실패:', error);
        alert('CIDR 추가에 실패했습니다.');
    }
}

// CIDR 수정 모달 열기
function editCidr(idx, button) {
    const form = document.getElementById('editCidrForm');
    form.idx.value = idx;
    form.list_type.value = button.parentElement.querySelector('.cidr-type').value;
    form.cidr.value = button.parentElement.querySelector('.cidr-value').value;
    form.description.value = button.parentElement.querySelector('.cidr-description').value;
    
    const modal = new bootstrap.Modal(document.getElementById('editCidrModal'));
    modal.show();
}

// CIDR 수정
async function updateCidr() {
    const form = document.getElementById('editCidrForm');
    const formData = new FormData(form);
    const idx = form.idx.value;
    
    try {
        const response = await fetch(`/api/cidrs/${idx}`, {
            method: 'PUT',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('editCidrModal')).hide();
            loadCidrs();
        } else {
            alert(data.message || 'CIDR 수정에 실패했습니다.');
        }
    } catch (error) {
        console.error('CIDR 수정 실패:', error);
        alert('CIDR 수정에 실패했습니다.');
    }
}

// CIDR 삭제
async function deleteCidr(idx) {
    if (!confirm('정말 이 CIDR을 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/cidrs/${idx}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadCidrs();
        } else {
            alert(data.message || 'CIDR 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('CIDR 삭제 실패:', error);
        alert('CIDR 삭제에 실패했습니다.');
    }
}

// CIDR 활성화/비활성화 토글
async function toggleActive(idx, currentActive) {
    const action = currentActive ? '비활성화' : '활성화';
    if (!confirm(`정말 이 CIDR을 ${action} 하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/cidrs/${idx}/toggle`, {
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
            loadCidrs();
        } else {
            alert(data.message || `CIDR ${action}에 실패했습니다.`);
        }
    } catch (error) {
        console.error(`CIDR ${action} 실패:`, error);
        alert(`CIDR ${action}에 실패했습니다.`);
    }
}

// 정렬 상태를 저장할 변수
let currentSort = { column: -1, ascending: true };

// 테이블 정렬 함수
function sortTable(columnIndex) {
    const tbody = document.getElementById('cidrTableBody');
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
            // 날짜 문자열을 Date 객체로 변환
            const aDate = new Date(a.querySelector('td[data-timestamp]').dataset.timestamp.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
            const bDate = new Date(b.querySelector('td[data-timestamp]').dataset.timestamp.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
            
            return currentSort.ascending ? aDate - bDate : bDate - aDate;
        }
        // 다른 열들
        else {
            const aCell = a.getElementsByTagName('td')[columnIndex];
            const bCell = b.getElementsByTagName('td')[columnIndex];
            aValue = aCell.dataset.cidr || aCell.dataset.description || aCell.textContent;
            bValue = bCell.dataset.cidr || bCell.dataset.description || bCell.textContent;
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
    
    loadCidrs();
}); 