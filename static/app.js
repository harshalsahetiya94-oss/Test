// === File Upload: Drag & Drop + File List ===
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const fileNames = document.getElementById('file-names');
    const uploadForm = document.getElementById('upload-form');
    const overlay = document.getElementById('processing-overlay');

    if (!dropZone) return;

    // Click to open file picker
    dropZone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON') {
            fileInput.click();
        }
    });

    // Drag events
    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        fileInput.files = dt.files;
        showFileList(dt.files);
    });

    fileInput.addEventListener('change', () => {
        showFileList(fileInput.files);
    });

    function showFileList(files) {
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

    // Show processing overlay on submit
    if (uploadForm) {
        uploadForm.addEventListener('submit', () => {
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
