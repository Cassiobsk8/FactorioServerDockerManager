# WORLD BUILDER SCHEMA

Versão: 3.1.0
Epic: World Builder V2
Card: WB-V2.1

---

## 1. Objetivo

Este documento descreve a camada de metadados oficial dos schemas do Factorio
utilizada pelo World Builder. Seu objetivo é fornecer uma representação
consistente e validada de:

- `map-gen-settings.json`
- `map-settings.json`

Nenhuma lógica de interface depende diretamente de JSON hardcoded.

---

## 2. Estrutura dos Arquivos

### 2.1 map-gen-settings.json

Controla a geração do mundo no momento da criação. Alterações só fazem efeito
em um novo save.

Campos principais:

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `seed` | uint32 \| null | null | Seed aleatória ou fixa |
| `width` | uint32 | 0 | Largura em tiles (0 = infinita) |
| `height` | uint32 | 0 | Altura em tiles (0 = infinita) |
| `starting_area` | MapGenSize | 1 | Multiplicador da zona segura inicial |
| `peaceful_mode` | boolean | false | Modo pacífico |
| `no_enemies_mode` | boolean | false | Sem inimigos |
| `autoplace_controls` | dict | — | Controles de frequência/tamanho/riqueza |
| `cliff_settings` | dict | — | Configuração de penhascos |
| `property_expression_names` | dict | — | Overrides de geradores de terreno |
| `starting_points` | array | [{x:0,y:0}] | Posições das áreas iniciais |
| `territory_settings` | dict | — | Configuração de território (Space Age) |

### 2.2 map-settings.json

Controla regras de simulação permanentes. Alterações fazem efeito imediato ou
após restart.

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `difficulty_settings` | dict | — | Multiplicadores de dificuldade |
| `pollution` | dict | — | Propagação e efeitos de poluição |
| `enemy_evolution` | dict | — | Evolução dos inimigos |
| `enemy_expansion` | dict | — | Expansão de bases inimigas |
| `unit_group` | dict | — | Comportamento de grupos de unidades |
| `path_finder` | dict | — | Configuração do pathfinder |
| `asteroids` | dict | — | Spawning de asteroides (Space Age) |
| `max_failed_behavior_count` | uint32 | 3 | Máximo de falhas antes de destruir inimigo |

---

## 3. Arquitetura

### 3.1 Módulo Dedicado

```
backend/services/world_builder_schema/
├── __init__.py
└── schema.py
```

### 3.2 Componentes

- `MAP_GEN_SETTINGS_SCHEMA`: lista de `FieldMetadata` para map-gen-settings
- `MAP_SETTINGS_SCHEMA`: lista de `FieldMetadata` para map-settings
- `load_schema_metadata()`: retorna metadados completos
- `validate_schema_integrity()`: valida ausência de duplicatas e categorias
- `get_categories()`: lista categorias válidas
- `get_fields_by_category(category)`: filtra campos por categoria
- `get_field_by_id(id)`: busca campo por ID

### 3.3 Formato do FieldMetadata

```python
@dataclass
class FieldMetadata:
    id: str
    label: str
    description: str
    category: str
    type: str
    default: Any = None
    options: list[str] | None = None
    min: float | int | None = None
    max: float | int | None = None
    unit: str | None = None
    source_file: str | None = None
    parent: str | None = None
    planet_exclusive: list[str] | None = None
    space_age_exclusive: bool = False
```

---

## 4. Categorias

- **Resources** — Recursos minerais e de petróleo
- **Terrain** — Terreno, elevação, penhascos
- **Water** — Água
- **Starting Area** — Área inicial do jogador
- **Enemies** — Inimigos, bases, grupos
- **Pollution** — Poluição
- **Evolution** — Evolução dos inimigos
- **Expansion** — Expansão de bases
- **Advanced** — Configurações avançadas/pathfinder
- **Planet** — Campos exclusivos de planeta (Space Age)

---

## 5. Diferenças entre map-gen-settings e map-settings

| Aspecto | map-gen-settings | map-settings |
|---------|------------------|--------------|
| Momento de aplicação | World-start only | Permanent / restart |
| Exemplo de campo | `autoplace_controls.coal` | `pollution.diffusion_ratio` |
| Frequência de alteração | Baixa | Alta |
| Suporte a planetas | Sim (por planeta) | Não (global) |
| Campos Space Age | `territory_settings`, cliffs por planeta | `asteroids`, `spoil_time_modifier` |

---

## 6. Campos Exclusivos do Space Age

### map-gen-settings

- `territory_settings.enabled`
- `territory_settings.force`
- `territory_settings.chunk_padding`
- `cliff_settings.cliff_smoothing`
- `autoplace_controls.fulgora_cliff`
- `autoplace_controls.gleba_cliff`

### map-settings

- `asteroids.spawning_rate`
- `asteroids.max_ray_portals_expanded_per_tick`
- `difficulty_settings.spoil_time_modifier`

---

## 7. Dependências entre Campos

- `cliff_settings.richness` depende de `cliff_settings.name`
- `property_expression_names` sobrescreve geradores padrão
- `starting_points` define posições das áreas iniciais
- `autoplace_controls` é ignorado se `default_enable_all_autoplace_controls` for false

---

## 8. Estratégia de Evolução Futura

1. **Versionamento**: o schema segue semver independente do projeto
2. **Extensibilidade**: novos campos são adicionados à lista correspondente
3. **Compatibilidade**: campos desconhecidos são preservados no JSON final
4. **Validação**: `validate_schema_integrity()` é executada no startup
5. **Interface**: nenhuma tela ou input é alterado por este card

---

## 9. Validação

### 9.1 Testes Automatizados

- `test_load_schema_metadata_returns_version`
- `test_load_schema_metadata_counts`
- `test_load_schema_metadata_categories`
- `test_load_schema_metadata_fields_are_dicts`
- `test_validate_schema_integrity_no_duplicates`
- `test_validate_schema_integrity_valid_categories`
- `test_validate_schema_integrity_source_files`
- `test_get_categories_returns_non_empty_list`
- `test_get_fields_by_category_resources`
- `test_get_fields_by_category_invalid`
- `test_get_field_by_id_existing`
- `test_get_field_by_id_map_settings`
- `test_get_field_by_id_nonexistent`
- `test_map_gen_schema_has_required_fields`
- `test_map_settings_schema_has_required_fields`
- `test_space_age_fields_marked`
- `test_planet_exclusive_fields`
- `test_schema_serializable`
- `test_map_gen_schema_field_types`
- `test_map_settings_schema_field_types`
- `test_no_duplicate_labels`
- `test_all_fields_have_description`

### 9.2 Execução

```bash
cd backend
pytest tests/test_world_builder_schema.py -v
```

---

## 10. Referências

- [Factorio Wiki - Command line parameters](https://wiki.factorio.com/Command_line_parameters)
- [Factorio Lua API - MapGenSettings](https://lua-api.factorio.com/latest/concepts/MapGenSettings.html)
- [Factorio Lua API - MapSettings](https://lua-api.factorio.com/latest/concepts/MapSettings.html)
- [wube/factorio-data - map-gen-settings.example.json](https://github.com/wube/factorio-data/blob/master/map-gen-settings.example.json)
- [wube/factorio-data - map-settings.example.json](https://github.com/wube/factorio-data/blob/master/map-settings.example.json)
