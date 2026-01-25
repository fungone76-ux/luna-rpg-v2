# file: core/memory_manager.py
from typing import List, Dict, Any
import time  # Fondamentale per la pausa


class MemoryManager:
    """
    Gestisce la memoria a breve termine (History), a lungo termine (Summaries)
    e la conoscenza permanente (Facts/Knowledge Base).
    """

    def __init__(self, state_manager, llm_client):
        self.state_manager = state_manager
        self.llm = llm_client

        # --- MODIFICA 1: FREQUENZA RIDOTTA ---
        # Aumentiamo il buffer per ridurre le volte in cui deve fermarsi a riassumere.
        self.HISTORY_LIMIT = 20  # Prima era 12. Ora tiene più scambi in RAM.
        self.PRUNE_COUNT = 10  # Quando pulisce, libera metà memoria in un colpo solo.

    def get_context_block(self) -> str:
        """
        Costruisce il blocco di testo da iniettare nel System Prompt o come User Message.
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
            context_text += "📜 PREVIOUS STORY SUMMARY:\n"
            for s in summaries:
                context_text += f"- {s}\n"
            context_text += "\n"

        return context_text

    def manage_memory_drift(self):
        """
        Controlla se la storia recente è troppo lunga e innesca la compressione.
        Include una pausa di sicurezza di 10 secondi per l'API.
        """
        history = self.state_manager.current_state.get("history", [])

        if len(history) > self.HISTORY_LIMIT:
            print(f"🧠 [MEMORY] Compressing old messages...")

            # Separa i messaggi da archiviare e quelli da tenere
            to_prune = history[:self.PRUNE_COUNT]
            remaining = history[self.PRUNE_COUNT:]

            # Genera il riassunto tramite LLM in sicurezza
            try:
                summary = self.llm.summarize_history(to_prune)

                if summary:
                    # Aggiorna lo stato solo se il riassunto è valido
                    if "summary_log" not in self.state_manager.current_state:
                        self.state_manager.current_state["summary_log"] = []

                    self.state_manager.current_state["summary_log"].append(summary)
                    self.state_manager.current_state["history"] = remaining

                    print(f"✅ [MEMORY] Archived: {summary[:50]}...")

                    # --- MODIFICA 2: PAUSA DI SICUREZZA 10 SECONDI ---
                    print("⏳ [MEMORY] Cooling down API (Safe Wait 10s)...")
                    time.sleep(10)
                    # -------------------------------------------------

                else:
                    print("⚠️ [MEMORY] Summary failed (empty response), skipping pruning this turn.")

            except Exception as e:
                print(f"❌ [MEMORY] Error during compression: {e}")
                # Se fallisce, non crasha il gioco, riproverà al prossimo turno.

    def add_fact(self, fact_text: str):
        """Aggiunge un fatto permanente alla Knowledge Base."""
        if not fact_text: return

        state = self.state_manager.current_state
        if "knowledge_base" not in state:
            state["knowledge_base"] = []

        # Evita duplicati esatti
        if fact_text not in state["knowledge_base"]:
            state["knowledge_base"].append(fact_text)
            print(f"🧠 [MEMORY] New Fact Learned: {fact_text}")