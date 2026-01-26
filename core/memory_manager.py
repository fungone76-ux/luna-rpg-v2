# file: core/memory_manager.py
from typing import List, Dict, Any
import time


class MemoryManager:
    """
    Gestisce la memoria a breve termine (History), a lungo termine (Summaries)
    e la conoscenza permanente (Facts/Knowledge Base).
    """

    def __init__(self, state_manager, llm_client):
        self.state_manager = state_manager
        self.llm = llm_client

        # --- CONFIGURAZIONE FREQUENZA (MOLTO RARA) ---
        # 50 messaggi = circa 25 turni completi.
        # Questo riduce drasticamente le interruzioni di gioco.
        self.HISTORY_LIMIT = 50
        self.PRUNE_COUNT = 20

    def get_context_block(self) -> str:
        """
        Costruisce il blocco di testo da iniettare nel System Prompt.
        Include: Fatti Chiave + Riassunti Passati.
        """
        state = self.state_manager.current_state
        summaries = state.get("summary_log", [])
        facts = state.get("knowledge_base", [])

        context_text = ""

        # 1. Fatti Chiave (Permanenti)
        if facts:
            context_text += "🧠 KNOWLEDGE BASE (IMPORTANT FACTS):\n"
            for fact in facts:
                context_text += f"- {fact}\n"
            context_text += "\n"

        # 2. Riassunti Narrativi (Episodici)
        if summaries:
            context_text += "📜 STORY SO FAR (Key Events):\n"
            for s in summaries:
                context_text += f"- {s}\n"
            context_text += "\n"

        return context_text

    def manage_memory_drift(self):
        """
        Controlla se la storia recente è troppo lunga e innesca la compressione.
        """
        history = self.state_manager.current_state.get("history", [])

        if len(history) > self.HISTORY_LIMIT:
            print(f"🧠 [MEMORY] Buffer limit reached ({len(history)}/{self.HISTORY_LIMIT}). Starting compression...")

            # Separa i messaggi da archiviare e quelli da tenere
            to_prune = history[:self.PRUNE_COUNT]
            remaining = history[self.PRUNE_COUNT:]

            try:
                # Chiama la funzione di riassunto (assicurati che media/llm_client.py sia aggiornato)
                summary = self.llm.summarize_history(to_prune)

                if summary:
                    # Aggiorna lo stato
                    if "summary_log" not in self.state_manager.current_state:
                        self.state_manager.current_state["summary_log"] = []

                    self.state_manager.current_state["summary_log"].append(summary)
                    self.state_manager.current_state["history"] = remaining

                    print(f"✅ [MEMORY] Archived: {summary[:60]}...")

                    # Pausa di sicurezza (avviene molto di rado ora)
                    print("⏳ [MEMORY] Saving changes (5s)...")
                    time.sleep(5)
                else:
                    print("⚠️ [MEMORY] Summary skipped (empty response).")

            except Exception as e:
                print(f"❌ [MEMORY] Error during compression: {e}")

    def add_fact(self, fact_text: str):
        """
        Aggiunge un fatto permanente alla Knowledge Base.
        Questa funzione mancava e causava il crash.
        """
        if not fact_text: return

        state = self.state_manager.current_state
        if "knowledge_base" not in state:
            state["knowledge_base"] = []

        # Evita duplicati esatti
        if fact_text not in state["knowledge_base"]:
            state["knowledge_base"].append(fact_text)
            print(f"🧠 [MEMORY] New Fact Learned: {fact_text}")