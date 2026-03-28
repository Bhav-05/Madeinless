const terminal = document.getElementById('live-terminal');
const logbook = document.getElementById('incident-logbook');

export function addTerminalLine(text, type, badgeText) {
    if (!terminal) return;
    const line = document.createElement('div');
    line.className = 'term-line';

    const timestamp = new Date().toISOString().split('T')[1].substring(0, 8);

    let badgeColor = '#94a0b3';
    if(type === 'term-info') badgeColor = '#3b79f6';
    if(type === 'term-warn') badgeColor = '#f5a623';
    if(type === 'term-crit') badgeColor = '#e04646';
    if(type === 'term-sys') badgeColor = '#5ee084';
    if(type === 'term-ai') badgeColor = '#3b79f6';

    let textColor = 'var(--text-main)';
    if(type === 'term-crit') textColor = '#e04646';
    if(type === 'term-warn') textColor = '#f5a623';

    line.innerHTML = `
        <span class="term-timestamp">${timestamp}</span>
        <span class="term-badge" style="background:${badgeColor}18; color:${badgeColor}; border:1px solid ${badgeColor}50;">${badgeText}</span>
        <span class="term-text" style="color:${textColor};">${text}</span>`;

    terminal.appendChild(line);
    
    if (terminal.childElementCount > 50) terminal.removeChild(terminal.firstChild);
    terminal.scrollTop = terminal.scrollHeight;
}

export function addLogbookEntry(service, issue, sla) {
    if (!logbook) return;
    const entry = document.createElement('div');
    entry.className = 'logbook-entry';
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="logbook-time">${timestamp}</span><span class="logbook-desc"><strong>${service}</strong>: ${issue}</span><span class="logbook-sla">SLA: ${sla}s</span>`;
    logbook.insertBefore(entry, logbook.firstChild);
}

export function initTerminal() {
    if(terminal) {
        terminal.innerHTML = '';
        addTerminalLine('System initialized. Connection to Loki stream established.', 'term-sys', 'SYS');
        addTerminalLine('Hugging Face NLP model loaded into memory.', 'term-sys', 'SYS');
    }
}

export function setupWidgetInteractions() {
    const widgets = document.querySelectorAll('.widget');
    let overlay = document.querySelector('.overlay');

    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'overlay';
        document.body.appendChild(overlay);
    }

    widgets.forEach(widget => {
        const closeBtn = document.createElement('span');
        closeBtn.className = 'close-btn';
        closeBtn.innerHTML = '×';
        widget.appendChild(closeBtn);

        widget.addEventListener('click', function(e) {
            if (e.target.classList.contains('close-btn') || e.target.tagName.toLowerCase() === 'button' || this.classList.contains('expanded') || this.classList.contains('animating')) return;
            
            const rect = this.getBoundingClientRect();
            
            const placeholder = document.createElement('div');
            placeholder.className = 'widget-placeholder';
            placeholder.style.gridColumn = getComputedStyle(this).gridColumn;
            placeholder.style.gridRow = getComputedStyle(this).gridRow;
            this.parentNode.insertBefore(placeholder, this);
            this.placeholderEl = placeholder;

            this.style.position = 'fixed';
            this.style.top = rect.top + 'px';
            this.style.left = rect.left + 'px';
            this.style.width = rect.width + 'px';
            this.style.height = rect.height + 'px';
            this.style.margin = '0';
            this.style.zIndex = '1000';

            this.offsetHeight; 

            this.classList.add('animating');
            this.classList.add('loading');
            overlay.classList.add('active');

            this.style.top = '5vh';
            this.style.left = '5vw';
            this.style.width = '90vw';
            this.style.height = '90vh';
            this.classList.add('expanded');

            setTimeout(() => { 
                this.classList.remove('loading');
                window.dispatchEvent(new Event('resize')); 
            }, 800);
        });

        closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const parentWidget = this.parentElement;
            if (!parentWidget || !parentWidget.placeholderEl) return;

            overlay.classList.remove('active');

            const internals = parentWidget.querySelectorAll('.detailed-content, .close-btn');
            internals.forEach(el => el.style.opacity = '0');

            const rect = parentWidget.placeholderEl.getBoundingClientRect();
            parentWidget.style.top = rect.top + 'px';
            parentWidget.style.left = rect.left + 'px';
            parentWidget.style.width = rect.width + 'px';
            parentWidget.style.height = rect.height + 'px';

            setTimeout(() => {
                parentWidget.classList.remove('expanded');
                parentWidget.classList.remove('animating');
                parentWidget.style.cssText = ''; 
                internals.forEach(el => el.style.opacity = ''); 
                if (parentWidget.placeholderEl) {
                    parentWidget.placeholderEl.remove();
                    parentWidget.placeholderEl = null;
                }
                window.dispatchEvent(new Event('resize'));
            }, 500); 
        });
    });
}