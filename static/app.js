// === File Upload: Drag & Drop + File List ===
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const fileNames = document.getElementById('file-names');
    const uploadForm = document.getElementById('upload-form');
    const overlay = document.getElementById('processing-overlay');
    const chooseBtn = document.getElementById('choose-btn');

    if (!dropZone || !fileInput) return;

    // "Choose Files" button opens file picker
    if (chooseBtn) {
        chooseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            fileInput.click();
        });
    }

    // Clicking the drop zone (but not the button) also opens file picker
    dropZone.addEventListener('click', (e) => {
        if (e.target === chooseBtn || (chooseBtn && chooseBtn.contains(e.target))) return;
        fileInput.click();
    });

    // Drag events
    dropZone.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        fileInput.files = e.dataTransfer.files;
        showFileList(e.dataTransfer.files);
    });

    // When files are chosen via picker
    fileInput.addEventListener('change', () => {
        showFileList(fileInput.files);
    });

    function showFileList(files) {
        if (!fileList || !fileNames) return;
        if (files.length === 0) {
            fileList.hidden = true;
            return;
        }

        fileNames.innerHTML = '';
        for (const f of files) {
            const li = document.createElement('li');
            li.textContent = `${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
            fileNames.appendChild(li);
        }
        fileList.hidden = false;
    }

    // Only show spinner when form is actually submitted WITH files
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            if (!fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                alert('Please select a file first.');
                return;
            }
            if (overlay) overlay.hidden = false;
        });
    }

    // Auto-dismiss flash messages after 8 seconds
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transition = 'opacity 0.3s';
            setTimeout(() => el.remove(), 300);
        }, 8000);
    });
});
