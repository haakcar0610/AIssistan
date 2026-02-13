# Mesajı aktif konuya ekle ve SUPABASE'E KAYDET
for konu in session["konular"]:
    if konu["id"] == session["aktif_konu"]:
        konu["mesajlar"].append({"role": "user", "content": user_message})
        # SUPABASE'E KAYDET
        save_message(user_id, konu["id"], "user", user_message)
        break
