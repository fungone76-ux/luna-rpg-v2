# file: core/prompt_dispatcher.py
from typing import Dict, List, Tuple, Any

# Importiamo i builder (Attenzione: builder_multi e builder_npc li creeremo a breve)
import core.prompt_builder as builder_single

# Placeholder per i moduli futuri (per evitare errori finché non esistono i file)
try:
    import core.prompt_builder_multi as builder_multi
except ImportError:
    builder_multi = None

try:
    import core.prompt_builder_npc as builder_npc
except ImportError:
    builder_npc = None


class PromptDispatcher:
    """
    Analizza TUTTO il contesto (Testo Narrativo + Visual + Tags)
    e decide la strategia di generazione (Singolo, Gruppo, NPC).
    """

    @staticmethod
    def dispatch(
            text_response: str,  # <--- NUOVO: La narrazione (es. "Luna ti guarda...")
            visual_en: str,
            tags_en: List[str],
            game_state: Dict[str, Any],
            world_data: Dict[str, Any]
    ) -> Tuple[str, str]:

        # 1. Analisi Profonda della Scena
        scene_type, subjects = PromptDispatcher._analyze_subjects(
            text_response, visual_en, tags_en, game_state, world_data
        )

        print(f"🚦 [DISPATCHER] Logic: {scene_type} | Subjects: {subjects}")

        # 2. Routing alle varie strategie
        if scene_type == "MULTI":
            if builder_multi:
                # Passiamo i soggetti trovati al builder multi
                return builder_multi.build_image_prompt(visual_en, tags_en, subjects, game_state, world_data)
            else:
                print("⚠️ Modulo Multi non ancora creato. Fallback su Singolo.")
                # Fallback: usiamo il primo personaggio della lista
                fallback_char = subjects[0] if subjects else "Luna"
                # Simuliamo uno stato temporaneo per forzare il personaggio singolo
                temp_state = game_state.copy()
                temp_state["game"]["companion_name"] = fallback_char
                return builder_single.build_image_prompt(visual_en, tags_en, temp_state, world_data)

        elif scene_type == "NPC":
            if builder_npc:
                npc_type = subjects[0]  # Es. "orc", "guard"
                return builder_npc.build_image_prompt(visual_en, tags_en, npc_type, game_state, world_data)
            else:
                print("⚠️ Modulo NPC non ancora creato. Fallback su Singolo.")
                return builder_single.build_image_prompt(visual_en, tags_en, game_state, world_data)

        else:  # CASE: SINGLE (Default)
            # Passiamo al builder singolo standard.
            # Nota: Possiamo aiutare il builder singolo dicendogli chi è il soggetto se diverso dalla compagna attuale
            target_char = subjects[0] if subjects else game_state.get("game", {}).get("companion_name", "Luna")

            # Se il soggetto rilevato è diverso dalla compagna "attiva" nel gioco, forziamo il builder a usare quello
            # (Esempio: Sei con Luna, ma incontri Stella da sola -> Genera Stella)
            if target_char in world_data.get("companions", {}):
                # Usiamo un trick non invasivo: il builder single controlla già il testo,
                # ma per sicurezza possiamo manipolare lo stato se necessario.
                pass

            return builder_single.build_image_prompt(visual_en, tags_en, game_state, world_data)

    @staticmethod
    def _analyze_subjects(
            narrative: str,
            visual: str,
            tags: List[str],
            state: Dict,
            world: Dict
    ) -> Tuple[str, List[str]]:
        """
        Scansiona Narrazione + Visual + Tags alla ricerca di Nomi Propri o Tipi NPC.
        Ritorna: ("SINGLE"|"MULTI"|"NPC", [lista_nomi_o_tipi])
        """
        # Uniamo tutto in un unico blocco di testo lowercase per la ricerca
        full_text = (narrative + " " + visual + " " + " ".join(tags)).lower()

        # --- A. Cerca Main Characters (Companions) ---
        known_companions = list(world.get("companions", {}).keys())
        found_main = []

        for name in known_companions:
            # Controllo semplice: se il nome è nel testo
            if name.lower() in full_text:
                found_main.append(name)

        # Rimuovi duplicati mantenendo l'ordine (es. ["Luna", "Luna"] -> ["Luna"])
        found_main = list(dict.fromkeys(found_main))

        # LOGICA PRIORITARIA:

        # 1. SE ci sono 2+ Main Characters -> MULTI
        if len(found_main) >= 2:
            return "MULTI", found_main

        # 2. SE c'è esattamente 1 Main Character -> SINGLE
        if len(found_main) == 1:
            return "SINGLE", found_main

        # --- B. Cerca NPC (Solo se nessun Main Character è stato trovato) ---
        # Se non si parla di Luna/Stella/Maria, forse si parla di un Orco o una Guardia?
        npc_logic = world.get("npc_logic", {})
        male_hints = npc_logic.get("male_hints", [])
        female_hints = npc_logic.get("female_hints", [])

        all_npc_hints = male_hints + female_hints

        for npc_keyword in all_npc_hints:
            # Cerchiamo la parola intera per evitare falsi positivi
            # (Es. evitare che "human" triggheri dentro "humanity")
            check_str = f" {npc_keyword} "
            if check_str in f" {full_text} " or full_text.startswith(npc_keyword):
                return "NPC", [npc_keyword]

        # --- C. Fallback Finale ---
        # Se non trovo NESSUNO (né nomi, né npc), uso la compagna attiva nel gioco
        current_companion = state.get("game", {}).get("companion_name", "Luna")
        return "SINGLE", [current_companion]