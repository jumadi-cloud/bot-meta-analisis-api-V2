<?php

use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Http;
use App\Http\Controllers\ChatController;

// Route utama - redirect ke chat
Route::get('/', function () {
    return redirect('/chat');
});

// Route untuk tampilan chat (frontend)
Route::get('/chat', [ChatController::class, 'index'])->name('chat.index');

// Route untuk mengirim pesan (Gemini & N8N)
Route::post('/chat', [ChatController::class, 'send'])->name('chat.send');

Route::get('/chat/sessions', [ChatController::class, 'getSessionsByWorkflow']);

// Route untuk melihat sesi chat tertentu
// ✅ PERBAIKAN: Tambahkan ->where('id', '.*')
Route::get('/chat/{id}', [ChatController::class, 'show'])->where('id', '.*')->name('chat.show');

// Route untuk membuat sesi chat baru
Route::post('/chat/new', [ChatController::class, 'new'])->name('chat.new');

// Route untuk menghapus sesi chat
// ✅ PERBAIKAN: Tambahkan ->where('id', '.*')
Route::delete('/chat/{id}', [ChatController::class, 'destroy'])->where('id', '.*')->name('chat.destroy');



// ===========================================================================
// 🔧 ROUTE PERBAIKAN: Webhook Proxy ke n8n dengan handling JSON yang tepat
// ===========================================================================

Route::post('/webhook/n8n', function () {
    $message = request()->input('message');
    $requestSessionId = request()->input('session_id');
    $userId = auth()->check() ? auth()->id() : 'guest';

    if (!$message) {
        return response()->json([
            'success' => false,
            'error' => 'Pesan tidak boleh kosong.'
        ], 400);
    }

    // Generate session ID jika belum ada
    $actualSessionId = $requestSessionId ?: 'N8N-' . now()->format('Ymd') . '-' . \Str::random(8);

    \Log::info('n8n Webhook Request', [
        'message' => $message,
        'session_id' => $actualSessionId,
        'request_session_id' => $requestSessionId,
        'user_id' => $userId
    ]);

    try {
        // ✅ PERBAIKAN: Bersihkan spasi di akhir URL
        $n8nWebhookUrl = rtrim(env('N8N_WEBHOOK_URL', 'https://lazalbahjahbarat.app.n8n.cloud/webhook/b7e38b65-d374-4c36-84c2-c0a70241d64f'), ' ');

        $response = Http::timeout(30)->post($n8nWebhookUrl, [
            'message' => $message,
            'session_id' => $actualSessionId,
            'user_id' => $userId,
            'timestamp' => now()->toISOString(),
        ]);

        $body = $response->body();
        
        // 🔥 PERBAIKAN: Log raw response untuk debugging
        \Log::info('n8n Raw Response', [
            'body' => $body,
            'body_length' => strlen($body),
            'status' => $response->status()
        ]);

        $aiResponse = 'Tidak ada respons dari n8n.';

        if ($response->successful()) {
            // Coba decode JSON dari n8n
            $decoded = json_decode($body, true);
            
            if (json_last_error() === JSON_ERROR_NONE) {
                // Jika berhasil decode JSON
                if (is_array($decoded) && count($decoded) > 0 && isset($decoded[0]['output'])) {
                    // Format: [{"output": "content"}] (array dari n8n)
                    $aiResponse = $decoded[0]['output'];
                } elseif (isset($decoded['output'])) {
                    // Format: {"output": "content"} (object langsung)
                    $aiResponse = $decoded['output'];
                } else {
                    // JSON valid tapi struktur tidak dikenali
                    $aiResponse = 'Format respons n8n tidak dikenali: ' . $body;
                }
            } else {
                // Jika decode gagal, gunakan respons mentah tapi bersihkan
                $cleanBody = trim(strip_tags($body));
                $aiResponse = $cleanBody ?: 'Respons kosong dari n8n';
            }
        }

        \Log::info('n8n Webhook Response', [
            'session_id' => $actualSessionId,
            'response_length' => strlen($aiResponse),
            'final_response' => \Str::limit($aiResponse, 100),
            'json_error' => json_last_error_msg(),
            'status' => 'success'
        ]);

        return response()->json([
            'success' => true,
            'data' => [
                'ai_response' => $aiResponse,
                'id' => $actualSessionId,
                'session_id' => $actualSessionId,
            ]
        ]);

    } catch (\Exception $e) {
        \Log::error('n8n Webhook Error:', [
            'session_id' => $actualSessionId,
            'message' => $e->getMessage(),
            'trace' => $e->getTraceAsString()
        ]);

        return response()->json([
            'success' => false,
            'error' => 'Gagal terhubung ke n8n. Coba lagi nanti.'
        ], 500);
    }
});
