async function generateReport() {
    const loader = document.getElementById('reportLoader');
    const contentArea = document.getElementById('printArea');
    const content = document.getElementById('reportContent');
    const placeholder = document.getElementById('reportPlaceholder');
    const downloadBtn = document.getElementById('downloadPdfBtn');
    const generateBtn = document.getElementById('generateBtn');

    // Reset widoku
    placeholder.classList.add('hidden');
    contentArea.classList.add('hidden');
    downloadBtn.classList.add('hidden');
    generateBtn.disabled = true;
    generateBtn.innerHTML = `Przetwarzanie...`;
    
    loader.classList.remove('hidden');
    loader.classList.add('flex');

    try {
        // ZASTOSOWANIE NOWEJ FUNKCJI: fetchWithAuth (brak konieczności ręcznego wklejania nagłówków!)
        const res = await fetchWithAuth(`${CONFIG.API_URL}/tasks/generate-report`);
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || "Błąd generowania raportu");
        }
        
        const data = await res.json();
        
        // Magia 1: Zamiana formatu Markdown (**, ##) na czysty, sformatowany HTML
        content.innerHTML = marked.parse(data.report);
        
        // Dodanie dzisiejszej daty do nagłówka dokumentu
        const dzisiaj = new Date().toLocaleDateString('pl-PL');
        document.getElementById('reportDate').innerText = `Data: ${dzisiaj}`;

        // Wyświetlenie gotowego raportu i aktywacja przycisku zapisu do PDF
        contentArea.classList.remove('hidden');
        downloadBtn.classList.remove('hidden');
        downloadBtn.classList.add('flex');
    } catch (e) {
        content.innerHTML = `<p class="text-red-500 font-bold">Błąd: ${e.message}</p>`;
        contentArea.classList.remove('hidden');
    } finally {
        loader.classList.add('hidden');
        loader.classList.remove('flex');
        generateBtn.disabled = false;
        generateBtn.innerHTML = `Odnów Raport`;
    }
}

// Magia 2: Funkcja eksportująca widok HTML bezpośrednio do pliku PDF
function downloadPDF() {
    const element = document.getElementById('printArea');
    
    // Konfiguracja parametrów generatora PDF
    const opt = {
        margin:       10,
        filename:     `Raport_Efektywnosci_${new Date().toLocaleDateString('pl-PL')}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    // Dodajemy wewnętrzny margines (padding), aby tekst w PDF nie dotykał krawędzi kartki
    element.classList.add('p-8');
    
    html2pdf().set(opt).from(element).save().then(() => {
        // Po udanym pobraniu przywracamy oryginalne marginesy na stronie internetowej
        element.classList.remove('p-8');
    });
}