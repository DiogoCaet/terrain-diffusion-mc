"""Regenerates Terrain Diffusion's worldgen data for Minecraft 26.3 from vanilla 26.3's own files.

Usage: python3 tools/port_data_26_3.py <minecraft-common-26.3.jar>

26.x changed the worldgen formats (noise settings: no aquifers/ore-vein flags, surface rule moved
to the `material_rule` registry, `chunk_surface_level` instead of `preliminary_surface_level`;
dimension types and biomes gained new fields). Each file starts from the vanilla 26.3 version and
gets Terrain Diffusion's changes applied, so it stays in step with vanilla:
- noise settings: the model's terrain, climate noises zeroed (biomes come from the model), no
  aquifers or ore veins, its own simple surface rule
- dimension types: overworld with the taller heights of each world scale
- biomes: forest/taiga/snowy taiga with sparse trees; grove made warm and treeless
"""
import json
import os
import sys
import zipfile

NS = 'terrain-diffusion-mc'
OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'main', 'resources', 'data')
DIMENSION_HEIGHTS = {'terrain_diffusion': 800, 'terrain_diffusion_scale_1': 464, 'terrain_diffusion_scale_2': 800,
                     'terrain_diffusion_scale_3': 1136, 'terrain_diffusion_scale_4': 1472,
                     'terrain_diffusion_scale_5': 1808, 'terrain_diffusion_scale_6': 2032}
NOISE_HEIGHT = 2032


def write(path, data):
    path = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def block(state):
    """A block rule; states with properties use the 26.x object form ({"id", "properties"})."""
    if '[' in state:
        name, props = state[:-1].split('[')
        state = {'id': name, 'properties': dict(p.split('=') for p in props.split(','))}
    return {'type': 'minecraft:block', 'result_state': state}


def biome_is(*biomes):
    return {'type': 'minecraft:biome', 'biome_is': list(biomes)}


def stone_depth(offset):
    return {'type': 'minecraft:stone_depth', 'offset': offset, 'surface_type': 'floor', 'add_surface_depth': False,
            'secondary_depth_range': 0}


def cond(condition, then):
    return {'type': 'minecraft:condition', 'if_true': condition, 'then_run': then}


def material_rule():
    """Terrain Diffusion's surface rule (1.21 surface_rule), in the 26.3 material_rule format; ore veins left out."""
    surface = [
        cond(biome_is('minecraft:desert'), block('minecraft:sand')),
        cond(biome_is('minecraft:badlands'), block('minecraft:red_sand')),
        cond(biome_is('minecraft:snowy_slopes'), block('minecraft:snow_block')),
        cond(biome_is('minecraft:frozen_peaks'), block('minecraft:snow_block')),
        cond(biome_is('minecraft:stony_peaks'), block('minecraft:stone')),
        cond(biome_is('minecraft:windswept_hills'), block('minecraft:stone')),
        cond(biome_is('minecraft:warm_ocean'), block('minecraft:sand')),
        cond(biome_is('minecraft:ocean'), block('minecraft:sand')),
        cond(biome_is('minecraft:cold_ocean', 'minecraft:frozen_ocean'), block('minecraft:gravel')),
        cond({'type': 'minecraft:y_above', 'anchor': {'absolute': 62}, 'surface_depth_multiplier': 0, 'add_stone_depth': False},
             block('minecraft:grass_block')),
        block('minecraft:dirt'),
    ]
    under = [
        cond(biome_is('minecraft:desert'), block('minecraft:sandstone')),
        cond(biome_is('minecraft:badlands'), block('minecraft:terracotta')),
        cond(biome_is('minecraft:snowy_slopes'), block('minecraft:stone')),
        cond(biome_is('minecraft:frozen_peaks'), block('minecraft:stone')),
        cond(biome_is('minecraft:stony_peaks', 'minecraft:windswept_hills'), block('minecraft:stone')),
        cond(biome_is('minecraft:warm_ocean'), block('minecraft:sand')),
        cond(biome_is('minecraft:ocean', 'minecraft:cold_ocean', 'minecraft:frozen_ocean'), block('minecraft:gravel')),
        block('minecraft:dirt'),
    ]
    return {'type': 'minecraft:sequence', 'sequence': [
        cond({'type': 'minecraft:vertical_gradient', 'random_name': 'minecraft:bedrock_floor',
              'true_at_and_below': {'absolute': -60}, 'false_at_and_above': {'absolute': -55}}, block('minecraft:bedrock')),
        cond({'type': 'minecraft:vertical_gradient', 'random_name': 'minecraft:deepslate',
              'true_at_and_below': {'absolute': 0}, 'false_at_and_above': {'absolute': 8}}, block('minecraft:deepslate[axis=y]')),
        cond(biome_is('minecraft:snowy_plains', 'minecraft:snowy_taiga', NS + ':snowy_taiga_sparse'),
             cond(stone_depth(-1), cond({'type': 'minecraft:water', 'offset': 0, 'surface_depth_multiplier': 0, 'add_stone_depth': False},
                                        block('minecraft:snow[layers=1]')))),
        cond(stone_depth(0), {'type': 'minecraft:sequence', 'sequence': surface}),
        cond(stone_depth(4), {'type': 'minecraft:sequence', 'sequence': under}),
    ]}


def main(jar):
    z = zipfile.ZipFile(jar)

    def vanilla(path):
        return json.loads(z.read('data/minecraft/' + path))

    old_settings = json.load(open(os.path.join(OUT, NS, 'worldgen', 'noise_settings', 'terrain_diffusion.json')))
    if 'surface_rule' in old_settings:  # first run on the 1.21 files
        bedrock = old_settings['surface_rule']['sequence'][0]['if_true']
        assert bedrock['true_at_and_below'] == {'absolute': -60}, 'surface rule changed upstream: update material_rule()'

    # Noise settings
    settings = vanilla('worldgen/noise_settings/overworld.json')
    settings.pop('aquifers', None)  # absent = no aquifers (TD had aquifers_enabled: false)
    settings.pop('debug_functions', None)
    settings['spawn_target'] = []
    settings['noise'] = {'min_y': -64, 'height': NOISE_HEIGHT}
    terrain = {'type': NS + ':terrain_diffusion'}
    settings['noise_router'] = {
        'temperature': 0, 'vegetation': 0, 'continents': 0, 'erosion': 0, 'depth': 0, 'ridges': 0,
        'chunk_surface_level': {'type': NS + ':terrain_diffusion', 'output': 'height'},
        'final_density': terrain,
    }
    settings['material_rule'] = NS + ':terrain_diffusion'
    write(f'{NS}/worldgen/noise_settings/terrain_diffusion.json', settings)
    write(f'{NS}/worldgen/material_rule/terrain_diffusion.json', material_rule())

    # Dimension types (one per world scale)
    for name, height in DIMENSION_HEIGHTS.items():
        dimension = vanilla('dimension_type/overworld.json')
        dimension['min_y'] = -64
        dimension['height'] = height
        dimension['logical_height'] = height
        write(f'{NS}/dimension_type/{name}.json', dimension)

    # Sparse-tree biomes
    for name, base, trees, sparse in (('forest_sparse', 'forest', 'minecraft:trees_birch_and_oak_leaf_litter', 'trees_birch_and_oak_sparse'),
                                      ('taiga_sparse', 'taiga', 'minecraft:trees_taiga', 'trees_taiga_sparse'),
                                      ('snowy_taiga_sparse', 'snowy_taiga', 'minecraft:trees_taiga', 'trees_taiga_sparse')):
        biome = vanilla(f'worldgen/biome/{base}.json')
        biome['features'] = [[f'{NS}:{sparse}' if f == trees else f for f in step] for step in biome['features']]
        assert any(f'{NS}:{sparse}' in step for step in biome['features']), f'{base} has no {trees}'
        write(f'{NS}/worldgen/biome/{name}.json', biome)
    for sparse, base in (('trees_birch_and_oak_sparse', 'trees_birch_and_oak_leaf_litter'), ('trees_taiga_sparse', 'trees_taiga')):
        feature = vanilla(f'worldgen/placed_feature/{base}.json')
        feature['placement'][0]['count']['distribution'] = [{'data': 3, 'weight': 9}, {'data': 4, 'weight': 1}]
        write(f'{NS}/worldgen/placed_feature/{sparse}.json', feature)

    # Grove: warm, dry and treeless (TD's override), on top of the 26.3 grove
    old_grove = json.load(open(os.path.join(OUT, 'minecraft', 'worldgen', 'biome', 'grove.json')))
    grove = vanilla('worldgen/biome/grove.json')
    grove['temperature'] = old_grove['temperature']
    grove['downfall'] = old_grove['downfall']
    grove['has_precipitation'] = old_grove['has_precipitation']
    grove['features'] = old_grove['features']
    write('minecraft/worldgen/biome/grove.json', grove)


if __name__ == '__main__':
    main(sys.argv[1])
