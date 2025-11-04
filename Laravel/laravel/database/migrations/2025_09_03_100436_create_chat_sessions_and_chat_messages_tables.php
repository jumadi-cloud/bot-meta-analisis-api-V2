<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Buat tabel chat_sessions terlebih dahulu
        Schema::create('chat_sessions', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->string('session_id', 100)->nullable();
            $table->string('title', 255)->nullable();
            $table->timestamps(); // created_at & updated_at
        });

        // Buat tabel chat_messages
        Schema::create('chat_messages', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->bigInteger('chat_session_id')->unsigned();
            $table->enum('role', ['user', 'ai']);
            $table->json('content');
            $table->timestamps();

            // Foreign key ke chat_sessions
            $table->foreign('chat_session_id')->references('id')->on('chat_sessions')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('chat_messages');
        Schema::dropIfExists('chat_sessions');
    }
};