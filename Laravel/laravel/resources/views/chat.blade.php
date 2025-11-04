<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Kevin AI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ asset('css/chat.css') }}">
</head>
<body class="h-screen flex flex-col">

        <!-- Debug Toggle (disabled for production) -->
    
    <button id="debug-toggle" class="debug-toggle">Debug</button>
    <div id="debug-panel" class="debug-panel">
        <div id="debug-content">Debug Info</div>
    </div>



    <!-- Header Atas (Mobile) -->
    <div class="sticky top-0 z-50 flex items-center justify-between px-4 py-3 bg-white border-b md:hidden">
        <button id="mobile-menu-toggle" class="text-gray-600 p-2">
            ☰ Menu
        </button>
        <div class="text-lg font-bold">Kevin AI</div>
        <div class="w-8"></div>
    </div>


    <div class="flex flex-1 overflow-hidden">
        <!-- Sidebar (Off-canvas di mobile, tetap di desktop) -->
        <div id="sidebar" class="fixed inset-y-0 left-0 z-50 bg-white border-r shadow-lg transform -translate-x-full transition-transform duration-300 ease-in-out md:relative md:translate-x-0 md:w-80">
            <div class="p-4 flex flex-col h-full">
                <div class="logo-container flex items-center gap-2 mb-4">
                    <div class="logo-icon w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">🤖</div>
                    <div>
                        <h1 class="font-bold">Kevin AI</h1>
                        <p class="text-xs opacity-80">My Chats</p>
                    </div>
                </div>
                <button id="new-chat-btn" class="w-full bg-white border border-gray-300 text-blue-600 rounded-lg p-2 mb-4">+ Chat Baru</button>
                <div id="chat-sidebar" class="overflow-y-auto flex-1">
                    @forelse ($chatSessions as $session)
                        <div 
                            class="chat-item {{ isset($currentSession) && $currentSession->id == $session->id ? 'bg-blue-100 text-blue-800' : '' }} p-3 mb-2 rounded-lg cursor-pointer"
                            data-session-id="{{ $session->id }}"
                            title="{{ $session->title ?? 'Chat baru' }}">
                            <div class="flex items-center">
                                <div class="chat-avatar w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm">AI</div>
                                <div class="ml-2 flex-1 min-w-0">
                                    <div class="chat-title text-sm font-medium truncate">{{ Illuminate\Support\Str::limit($session->title ?? 'Chat baru', 30) }}</div>
                                    <div class="chat-time text-xs text-gray-500">{{ $session->created_at->format('H:i') }}</div>
                                </div>
                            </div>
                        </div>
                    @empty
                        <p id="empty-message" class="text-xs text-gray-500 text-center py-4">Belum ada percakapan</p>
                    @endforelse
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="flex-1 flex flex-col overflow-hidden bg-white">
            <!-- Header Agent (Desktop & Mobile) -->
            <div class="p-4 border-b block">
                <div class="flex flex-col gap-2">
                    <select id="workflow-type" class="model-select w-full p-2 border border-gray-300 rounded-md">
                        <option value="" disabled selected>Pilih Agent</option>
                        <option value="workflow1">Agent Meta ads</option>
                        <option value="workflow2">Agent Google ads</option>
                        <option value="workflow3">Agent Admin Apps</option>
                    </select>
                    <div class="text-xs text-gray-500 mt-1">
                        Mode: <span id="current-model">-</span>
                    </div>
                </div>
            </div>

            <!-- Chat Area -->
            <div id="chat-messages" class="flex-1 p-4 overflow-y-auto">
                @if(isset($messages) && count($messages) > 0)
                    @foreach($messages as $msg)
                        <div class="message {{ $msg->role === 'user' ? 'user' : 'assistant' }} mb-4">
                            <div class="message-content p-3 rounded-lg border border-gray-200 bg-white max-w-[80%] break-words">
                                {!! 
                                    str_replace(["\n"], ['<br>'],
                                        str_replace(['**'], ['<strong>', '</strong>'],
                                            str_replace(['*'], ['<em>', '</em>'],
                                                e($msg->content)
                                            )
                                        )
                                    )
                                !!}
                            </div>
                        </div>
                    @endforeach
                @else
                    <div class="welcome-message text-center py-10">
                        <div class="welcome-icon text-6xl">🤖</div>
                        <p class="welcome-title text-xl font-bold text-blue-600">Selamat datang!</p>
                        <p class="welcome-subtitle text-gray-500">Mulai percakapan dengan ketik pesan di bawah</p>
                    </div>
                @endif
            </div>

            <!-- Typing Indicator -->
            <div id="typing-indicator" class="typing-indicator" style="padding: 0 24px;">
                <div class="typing-content">
                    AI sedang mengetik...
                </div>
            </div>

            <!-- Input Area -->
            <div class="p-4 bg-white border-t">
                <div class="input-container flex gap-2">
                    <input
                        type="text"
                        id="message-input"
                        placeholder="Ketik pesan..."
                        class="message-input flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        autocomplete="off"
                        maxlength="2000"
                    />
                    <button
                        id="send-btn"
                        class="send-button bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 min-w-[80px]">
                        <span id="send-text">Kirim</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Context Menu -->
    <div id="context-menu" class="context-menu hidden">
        <div id="delete-chat" class="context-menu-item delete">
            <span>🗑️</span> Hapus Chat
        </div>
        <div class="context-menu-divider"></div>
        <div id="close-menu" class="context-menu-item">
            <span>❌</span> Tutup
        </div>
    </div>

    <script src="{{ asset('js/chats.js') }}"></script>
</body>
</html>