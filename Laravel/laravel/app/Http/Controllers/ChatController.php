<?php

namespace App\Http\Controllers;

use App\Models\ChatSession;
use App\Models\ChatMessage;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class ChatController extends Controller
{
    /**
 * Tampilkan halaman utama
 */
    public function index(Request $request)
    {
        Log::info('Index called with workflow:', ['workflow' => $request->get('workflow')]);
        $currentSessionId = $request->get('session_id');
        $selectedWorkflow = $request->get('workflow'); // workflow1, workflow2, atau workflow3
    
        // Mapping workflow ke role agent
        $roleMap = [
            'workflow1' => 'Agent Meta Ads',
            'workflow2' => 'Agent Google Ads',
            'workflow3' => 'Agent Admin Ads',
        ];
    
        $currentSession = null;
        $messages = collect();
    
        if ($currentSessionId) {
            $currentSession = ChatSession::find($currentSessionId);
            if ($currentSession) {
                $messages = $currentSession->messages()->orderBy('created_at', 'asc')->get();
            }
        }
    
        // Ambil semua session_id yang memiliki pesan AI dengan role sesuai filter
        $query = ChatMessage::where('role', '!=', 'user')
            ->select('chat_session_id')
            ->groupBy('chat_session_id');
    
        if ($selectedWorkflow && isset($roleMap[$selectedWorkflow])) {
            $query->where('role', $roleMap[$selectedWorkflow]);
        }
    
        $allowedSessionIds = $query->pluck('chat_session_id');
    
        // Ambil sesi yang sesuai
        $chatSessions = ChatSession::whereIn('id', $allowedSessionIds)
            ->latest()
            ->get();
    
        return view('chat', compact('chatSessions', 'currentSession', 'messages'));
    }

    /**
     * Dapatkan detail sesi chat
     */
    public function show($id)
    {
        try {
            $session = ChatSession::with('messages')->findOrFail($id);

            return response()->json([
                'success' => true,
                'data' => [
                    'id' => $session->id,
                    'title' => $session->title,
                    'messages' => $session->messages->map(function ($msg) {
                        return [
                            'role' => $msg->role,
                            'content' => $msg->content,
                            'created_at' => $msg->created_at->format('Y-m-d H:i:s')
                        ];
                    })
                ]
            ]);
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'error' => 'Chat tidak ditemukan'
            ], 404);
        }
    }
    
    public function getSessionsByWorkflow(Request $request)
    {
        $workflow = $request->get('workflow');
        $roleMap = [
            'workflow1' => 'Agent Meta Ads',
            'workflow2' => 'Agent Google Ads',
            'workflow3' => 'Agent Admin Ads',
        ];
    
        $query = ChatMessage::where('role', '!=', 'user')
            ->select('chat_session_id')
            ->groupBy('chat_session_id');
    
        if ($workflow && isset($roleMap[$workflow])) {
            $query->where('role', $roleMap[$workflow]);
        }
    
        $allowedSessionIds = $query->pluck('chat_session_id');
        $sessions = ChatSession::whereIn('id', $allowedSessionIds)->latest()->get();
    
        return response()->json([
            'success' => true,
            'data' => $sessions->map(function ($session) {
                return [
                    'id' => $session->id,
                    'title' => $session->title,
                    'created_at' => $session->created_at->format('H:i')
                ];
            })
        ]);
    }

    /**
     * Mulai sesi chat baru
     */
    public function new()
    {
        return response()->json([
            'success' => true,
            'message' => 'Siap mulai chat baru'
        ]);
    }

    /**
     * Kirim pesan dan dapatkan respons AI (Gemini atau n8n)
     */
    /**
     * Kirim pesan dan dapatkan respons AI (Gemini atau n8n)
     */
    public function send(Request $request)
    {
        try {
            $request->validate([
                'message' => 'required|string|max:2000',
                'session_id' => 'nullable|string',
                'model' => 'nullable|in:gemini,n8n'
            ]);
    
            $userMessage = $request->input('message');
            $requestSessionId = $request->input('session_id');
            $model = $request->input('model', 'gemini');
    
            Log::info('Chat send request received', [
                'message' => Str::limit($userMessage, 50),
                'session_id' => $requestSessionId,
                'model' => $model
            ]);
    
            // Cari session pakai primary key id
            $chatSession = $requestSessionId
                ? ChatSession::find($requestSessionId)
                : null;
    
            if (!$chatSession) {
                $chatSession = ChatSession::create([
                    'title' => Str::limit($userMessage, 50)
                ]);
            }
    
            // Simpan pesan user
            ChatMessage::create([
                'chat_session_id' => $chatSession->id,
                'role' => 'user',
                'content' => $userMessage
            ]);
    
            $aiResponse = "Halo, ini jawaban dummy dari model: {$model}";
            $aiRole = 'assistant'; // Default role untuk AI
    
            if ($model === 'n8n') {
                Log::info('Starting n8n request processing', ['model' => $model]);
            
                $type = $request->input('type', 'workflow1');
    
                // Mapping role berdasarkan workflow
                $agentRoles = [
                    'workflow1' => 'Agent Meta Ads',
                    'workflow2' => 'Agent Google Ads',
                    'workflow3' => 'Agent Admin Ads',
                ];
                $aiRole = $agentRoles[$type] ?? 'assistant'; // Gunakan role kustom atau fallback ke 'assistant'
    
                switch ($type) {
                    case 'workflow1':
                        $n8nUrl = env('N8N_WEBHOOK_URL', null); // default
                        break;
                    case 'workflow2':
                        $n8nUrl = env('N8N_WEBHOOK_URL2', env('N8N_WEBHOOK_URL'));
                        break;
                    case 'workflow3':
                        $n8nUrl = env('N8N_WEBHOOK_URL3', env('N8N_WEBHOOK_URL'));
                        break;
                    default:
                        $n8nUrl = env('N8N_WEBHOOK_URL');
                        break;
                }
            
                if ($n8nUrl) {
                    Log::info('Making request to n8n', ['url' => $n8nUrl]);
            
                    $n8nResponse = Http::timeout(120)->post($n8nUrl, [
                        'message' => $userMessage,
                        'session_id' => $chatSession->id,
                        'user_id' => auth()->id() ?? 'guest',
                        'timestamp' => now()->toISOString(),
                    ]);
            
                    Log::info('n8n response received', [
                        'successful' => $n8nResponse->successful(),
                        'status' => $n8nResponse->status()
                    ]);
    
                    if ($n8nResponse->successful()) {
                        $body = $n8nResponse->body();
                        
                        Log::info('n8n Raw Response', [
                            'body' => $body,
                            'body_length' => strlen($body),
                            'status' => $n8nResponse->status(),
                            'headers' => $n8nResponse->headers()
                        ]);
                    
                        // Coba decode JSON dari n8n
                        $decoded = json_decode($body, true);
                        
                        if (json_last_error() === JSON_ERROR_NONE) {
                            if (is_array($decoded) && count($decoded) > 0 && isset($decoded[0]['output'])) {
                                $aiResponse = $decoded[0]['output'];
                            } elseif (isset($decoded['output'])) {
                                $aiResponse = $decoded['output'];
                            } else {
                                $aiResponse = 'Format respons n8n tidak dikenali: ' . $body;
                            }
                        } else {
                            $cleanBody = trim($body, '"');
                            $cleanBody = str_replace('\n', "\n", $cleanBody);
                            $cleanBody = str_replace('\"', '"', $cleanBody);
                            
                            $decodedClean = json_decode($cleanBody, true);
                            if (json_last_error() === JSON_ERROR_NONE) {
                                if (is_array($decodedClean) && count($decodedClean) > 0 && isset($decodedClean[0]['output'])) {
                                    $aiResponse = $decodedClean[0]['output'];
                                } elseif (isset($decodedClean['output'])) {
                                    $aiResponse = $decodedClean['output'];
                                } else {
                                    $aiResponse = $cleanBody ?: 'Respons kosong dari n8n';
                                }
                            } else {
                                $aiResponse = $cleanBody ?: 'Respons kosong dari n8n';
                            }
                        }
                        
                        Log::info('n8n Processed Response', [
                            'final_response' => $aiResponse,
                            'final_response_length' => strlen($aiResponse),
                            'json_error' => json_last_error_msg(),
                            'decoded_type' => gettype($decoded ?? null)
                        ]);
                        
                    } else {
                        Log::error('n8n Request Failed', [
                            'status' => $n8nResponse->status(),
                            'body' => $n8nResponse->body()
                        ]);
                        $aiResponse = 'Tidak ada respons dari n8n. Silakan coba lagi.';
                    }
    
                } else {
                    $aiResponse = 'Webhook n8n tidak dikonfigurasi. Hubungi admin.';
                }
            }
    
            // Simpan balasan AI dengan role yang sesuai (bisa 'assistant', 'Agent Meta Ads', dll)
            ChatMessage::create([
                'chat_session_id' => $chatSession->id,
                'role' => $aiRole, // 👈 INI SATU-SATUNYA PERUBAHAN UTAMA
                'content' => $aiResponse
            ]);
    
            // Build response untuk frontend
            $responseMessages = $chatSession->messages()
                ->orderBy('created_at', 'asc')
                ->get(['role', 'content']);
    
            return response()->json([
                'success' => true,
                'data' => [
                    'session_id' => $chatSession->id,
                    'messages' => $responseMessages,
                    'ai_response' => $aiResponse
                ]
            ]);
    
        } catch (\Exception $e) {
            Log::error('Error in send', [
                'error' => $e->getMessage(),
                'file' => $e->getFile(),
                'line' => $e->getLine(),
            ]);
    
            return response()->json([
                'success' => false,
                'error' => 'Terjadi kesalahan: ' . $e->getMessage()
            ], 500);
        }
    }

    /**
     * Hapus sesi chat
     */
    public function destroy($id)
    {
        try {
            $session = ChatSession::findOrFail($id);
            $session->delete();

            return response()->json([
                'success' => true,
                'message' => 'Sesi berhasil dihapus'
            ]);
        } catch (\Exception $e) {
            Log::error('Failed to delete session', ['id' => $id, 'error' => $e->getMessage()]);
            return response()->json([
                'success' => false,
                'error' => 'Gagal menghapus sesi'
            ], 500);
        }
    }
}