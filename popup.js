document.getElementById("downloadBtn").addEventListener("click", async () => {
  const url = document.getElementById("urlInput").value;
  const statusEl = document.getElementById("status");
  const cancelBtn = document.getElementById("cancelBtn");
  const format = document.querySelector('input[name="format"]:checked').value; // Ambil format yang dipilih

  if (!url) {
    statusEl.textContent = "Masukkan URL terlebih dahulu!";
    return;
  }

  currentDownloadId = new Date().getTime().toString();
  statusEl.textContent = `Mengunduh video dalam format ${format.toUpperCase()}...`;
  cancelBtn.disabled = false;

  try {
    const response = await fetch("http://141.11.190.106:61000/download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url, id: currentDownloadId, format }), // Kirim format
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Gagal mengunduh video");

    statusEl.textContent = `Download selesai! File akan segera diunduh...`;

    setTimeout(() => {
      if (result.file) {
        window.location.href = `http://141.11.190.106:61000/files/${currentDownloadId}`;
      } else {
        statusEl.textContent = "Download gagal!";
      }
    }, 2000);
  } catch (error) {
    statusEl.textContent = "Error: " + error.message;
    cancelBtn.disabled = true;
  }
});

document.getElementById("cancelBtn").addEventListener("click", async () => {
  const statusEl = document.getElementById("status");
  const cancelBtn = document.getElementById("cancelBtn");

  if (!currentDownloadId) {
    statusEl.textContent = "Tidak ada download yang dapat dibatalkan!";
    return;
  }

  try {
    const response = await fetch("http://141.11.190.106:61000/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: currentDownloadId }),
    });

    const result = await response.json();
    if (!response.ok)
      throw new Error(result.error || "Gagal membatalkan download!");

    statusEl.textContent = "Download dibatalkan!";
    cancelBtn.disabled = true; // Nonaktifkan tombol setelah pembatalan
    currentDownloadId = null; // Reset ID agar tidak bisa cancel lagi
  } catch (error) {
    statusEl.textContent = "Error: " + error.message;
  }
});
