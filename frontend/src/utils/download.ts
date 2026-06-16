import { API_BASE } from '../api';

const extractFileName = (contentDisposition: string | null, fallbackName: string) => {
  if (!contentDisposition) {
    return fallbackName;
  }

  const utfMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1]);
  }

  const plainMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
  return plainMatch?.[1] || fallbackName;
};

export const downloadBlueprintFile = async (downloadUrl: string, fallbackName: string) => {
  const response = await fetch(`${API_BASE}${downloadUrl.replace(/^\/api/, '')}`);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Download failed with status ${response.status}`);
  }

  const blob = await response.blob();
  const fileName = extractFileName(response.headers.get('Content-Disposition'), fallbackName);

  if (window.repoBlueprintDesktop?.saveFile) {
    const arrayBuffer = await blob.arrayBuffer();
    const uint8 = new Uint8Array(arrayBuffer);
    let binary = '';
    const chunkSize = 0x8000;
    for (let i = 0; i < uint8.length; i += chunkSize) {
      binary += String.fromCharCode(...uint8.subarray(i, i + chunkSize));
    }
    const base64 = btoa(binary);
    const saved = await window.repoBlueprintDesktop.saveFile({
      base64,
      defaultFileName: fileName,
    });
    if (!saved) {
      throw new Error('Save was cancelled');
    }
    return;
  }

  if (window.showSaveFilePicker) {
    const picker = await window.showSaveFilePicker({
      suggestedName: fileName,
      types: [
        {
          description: 'Markdown Blueprint',
          accept: { 'text/markdown': ['.md'] },
        },
      ],
    });
    const writable = await picker.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }

  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
};
