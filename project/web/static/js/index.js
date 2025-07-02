$(document).ready(function() {
    // DataTables 초기화
    const table = $('#logs-table').DataTable({
        order: [[0, 'desc']],  // 시간 기준 내림차순 정렬
        pageLength: 25,
        language: {
            url: '//cdn.datatables.net/plug-ins/1.10.24/i18n/Korean.json'
        }
    });
    const logTableBody = document.querySelector('#logTable tbody');
    const errorContainer = document.createElement('div');
    errorContainer.className = 'alert alert-danger d-none';
    document.querySelector('.card-body').insertBefore(errorContainer, document.querySelector('.table-responsive'));
    
    // 정렬 상태를 저장할 변수
    let currentSort = {
        column: null,
        direction: 'asc'
    };

    // 테이블 정렬 함수
    function sortTable(columnIndex) {
        const tbody = document.getElementById('logTableBody');
        const rows = Array.from(tbody.getElementsByTagName('tr'));
        const headers = document.querySelectorAll('th');
        const currentHeader = headers[columnIndex];

        // 정렬 방향 결정
        if (currentSort.column === columnIndex) {
            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort.column = columnIndex;
            currentSort.direction = 'asc';
        }

        // 정렬 아이콘 업데이트
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            const icon = header.querySelector('i');
            if (icon) icon.className = 'bi bi-arrow-down-up';
        });

        const icon = currentHeader.querySelector('i');
        if (icon) {
            icon.className = `bi bi-arrow-${currentSort.direction === 'asc' ? 'up' : 'down'}`;
            currentHeader.classList.add(`sort-${currentSort.direction}`);
        }

        // 데이터 정렬
        rows.sort((a, b) => {
            let aValue = a.cells[columnIndex].textContent.trim();
            let bValue = b.cells[columnIndex].textContent.trim();

            // 날짜 열인 경우
            if (columnIndex === 3) {
                // 날짜 문자열을 Date 객체로 변환
                const aDate = new Date(aValue.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
                const bDate = new Date(bValue.replace(/(\d{4}). (\d{1,2}). (\d{1,2}). (\d{1,2}):(\d{1,2}):(\d{1,2})/, '$1-$2-$3T$4:$5:$6'));
                
                return currentSort.direction === 'asc' 
                    ? aDate - bDate
                    : bDate - aDate;
            }

            // 일반 텍스트 정렬
            return currentSort.direction === 'asc'
                ? aValue.localeCompare(bValue)
                : bValue.localeCompare(aValue);
        });

        // 정렬된 행을 다시 테이블에 추가
        rows.forEach(row => tbody.appendChild(row));
    }
    
    // 로그 데이터를 테이블에 추가하는 함수
    function appendLogToTable(log) {
        const timestamp = new Date(log.timestamp);
        const formattedDate = timestamp.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <span class="badge ${log.decision === 'allow' ? 'badge-allow' : 'badge-deny'}"
                      onclick="showReasonModal('${log.decision}', '${log.reason || '사유 없음'}')">${log.decision}</span>
            </td>
            <td class="ip-cell">${log.client_ip || ''}</td>
            <td>${log.url || ''}</td>
            <td data-timestamp="${log.timestamp}">${formattedDate}</td>
        `;
        logTableBody.appendChild(row);
    }
    
    // 에러 메시지 표시 함수
    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.classList.remove('d-none');
    }
    
    // 에러 메시지 숨기기 함수
    function hideError() {
        errorContainer.classList.add('d-none');
    }
    
    // 로그 데이터 로드
    function loadLogs() {
        hideError();
        
        fetch('/api/logs')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    logTableBody.innerHTML = ''; // 테이블 초기화
                    if (data.data.length === 0) {
                        showError('로그 데이터가 없습니다.');
                    } else {
                        data.data.forEach(log => appendLogToTable(log));
                        // 현재 정렬 상태가 있다면 다시 정렬 적용
                        if (currentSort.column !== null) {
                            sortTable(currentSort.column);
                        }
                    }
                } else {
                    showError(data.message || '로그 로드 중 오류가 발생했습니다.');
                }
            })
            .catch(error => {
                console.error('로그 로드 실패:', error);
                showError('로그를 가져오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
            });
    }
    
    // IP로 필터링하는 함수
    window.filterByIP = function(ip) {
        const filterBadge = document.getElementById('filterBadge');
        const filteredIP = document.getElementById('filteredIP');
        
        filteredIP.textContent = ip;
        filterBadge.style.display = 'inline-flex';
        
        const rows = logTableBody.querySelectorAll('tr');
        rows.forEach(row => {
            const sourceIP = row.querySelector('.ip-cell').textContent;
            row.style.display = sourceIP === ip ? '' : 'none';
        });
    };
    
    // 필터 제거
    window.clearFilter = function() {
        document.getElementById('filterBadge').style.display = 'none';
        const rows = logTableBody.querySelectorAll('tr');
        rows.forEach(row => row.style.display = '');
    };

    // 사유 모달 표시 함수
    window.showReasonModal = function(decision, reason) {
        const modal = new bootstrap.Modal(document.getElementById('reasonModal'));
        const modalTitle = document.querySelector('#reasonModal .modal-title');
        const modalReason = document.getElementById('modalReason');
        
        modalTitle.textContent = decision === 'allow' ? '허용 사유' : '차단 사유';
        modalReason.textContent = reason;
        modal.show();
    };

    // 검색 기능
    document.getElementById('logSearch').addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#logTableBody tr');

        rows.forEach(row => {
            const text = Array.from(row.children)
                .map(cell => cell.textContent.toLowerCase())
                .join(' ');
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    });
    
    // 테이블 헤더에 정렬 이벤트 리스너 추가
    const headers = document.querySelectorAll('th');
    headers.forEach((header, index) => {
        header.addEventListener('click', () => sortTable(index));
    });
    
    // 초기 로그 로드
    loadLogs();
    
    // 5초마다 로그 갱신
    setInterval(loadLogs, 5000);
}); 