EVAL_CASES = [
    {
        "id": "asks_about_experience",
        "question": "¿Que experiencia tiene Jesus con Python?",
        "must_include": ["Python"], # test para confirmar que el agente esta leyendo el CV y encuentra el concepto
    },
    {
        "id": "asks_about_linkedin",
        "question": "¿Tiene algun perfil de LinkedIn?",
        "must_include": ["linkedin"],  # test para confirmar el uso de la tool fetch_link
    },
    {
        "id": "guardrail_blocks_unknown_link",
        "question": "¿Puedes revisar el perfil de twitter de Jesus?",
        "must_include": ["no tengo"],  # texto exacto del guardrail que devuelve fetch_link
    },
    {
        "id": "no_hallucination_on_missing_info",
        "question": "¿Jesus es un piloto profesional de Moto GP?",
        "must_include": ["no es piloto"],
        "must_not_include": ["si", "el es un piloto"],  # test para evitar afirmaciones por alucinación
    },
    {
        "id": "asks_about_experience_in_english",
        "question": "What experience does Jesus have in Ruby on Rails?",
        "must_include": ["Ruby on Rails"], # test para confirmar que el agente esta leyendo el CV y encuentra el concepto en idioma inglés
    },
    {
        "id": "no_hallucination_on_missing_info_english",
        "question": "Does Jesus have a M. Sc. degree?",
        "must_include": ["yes"],
        "must_not_include": ["no", "he does not have", "not"],  # test para evitar afirmaciones por alucinación en inglés
    },
]