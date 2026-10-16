package com.github.xandergos.terraindiffusionmc.world;

import com.github.xandergos.terraindiffusionmc.config.TerrainDiffusionConfig;
import com.github.xandergos.terraindiffusionmc.pipeline.LocalTerrainProvider;
import com.github.xandergos.terraindiffusionmc.pipeline.LocalTerrainProvider.HeightmapData;
import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import net.minecraft.util.Interval;
import net.minecraft.util.StringRepresentable;
import net.minecraft.world.level.levelgen.densityfunction.DensityBuffer;
import net.minecraft.world.level.levelgen.densityfunction.DensityFunction;
import net.minecraft.world.level.levelgen.densityfunction.DensitySampler;
import net.minecraft.world.level.levelgen.densityfunction.DensityVolume;
import net.minecraft.world.level.levelgen.densityfunction.DfRewriteRule;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;

/**
 * The terrain from the diffusion model. 26.3 port: density functions compile to samplers.
 *
 * <ul>
 *   <li>{@code density} (default, for {@code final_density}): {@code height - y}, solid below the surface</li>
 *   <li>{@code height} (for {@code chunk_surface_level}, which 26.x expects as a block height): the surface height</li>
 * </ul>
 */
public record TerrainDiffusionDensityFunction(Output output) implements DensityFunction {
    public enum Output implements StringRepresentable {
        DENSITY("density"),
        HEIGHT("height");

        public static final Codec<Output> CODEC = StringRepresentable.fromEnum(Output::values);
        private final String name;

        Output(String name) {
            this.name = name;
        }

        @Override
        public String getSerializedName() {
            return this.name;
        }
    }

    public static final MapCodec<TerrainDiffusionDensityFunction> CODEC =
            Output.CODEC.optionalFieldOf("output", Output.DENSITY).xmap(TerrainDiffusionDensityFunction::new, TerrainDiffusionDensityFunction::output);

    @Override
    public DensitySampler compileSampler(DensityFunction.CompileContext context) {
        return new Sampler(this.output);
    }

    @Override
    public DensityFunction rewriteChildren(DfRewriteRule rule) {
        return this;
    }

    @Override
    public Interval range() {
        return Interval.of(-2048.0F, 2048.0F);
    }

    @Override
    public @DensityFunction.Axes int domainAxes() {
        // Height varies with x and z; density also with y.
        return this.output == Output.HEIGHT ? AXIS_X | AXIS_Z : ALL_AXES;
    }

    @Override
    public MapCodec<TerrainDiffusionDensityFunction> codec() {
        return CODEC;
    }

    /** Surface height at a block column (0 while the tile isn't available, as before the port). */
    private static int surfaceHeight(Tile tile, int x, int z) {
        tile.update(x, z);
        HeightmapData data = tile.data;
        if (data == null || data.heightmap == null) {
            return 0;
        }
        int localX = Math.max(0, Math.min(data.width - 1, x - tile.blockStartX));
        int localZ = Math.max(0, Math.min(data.height - 1, z - tile.blockStartZ));
        return HeightConverter.convertToMinecraftHeight(data.heightmap[localZ][localX]);
    }

    private record Sampler(Output output) implements DensitySampler {
        @Override
        public float sampleValue(SamplerContext context, int blockX, int blockY, int blockZ) {
            int height = surfaceHeight(new Tile(), blockX, blockZ);
            return this.output == Output.HEIGHT ? height : height - blockY;
        }

        @Override
        public void sampleVolume(SamplerContext context, DensityBuffer outputBuffer, DensityVolume volume) {
            // One tile lookup per column instead of per block.
            Tile tile = new Tile();
            for (int z = 0; z < volume.sizeZ(); z++) {
                int blockZ = volume.blockZ(z);
                for (int x = 0; x < volume.sizeX(); x++) {
                    int blockX = volume.blockX(x);
                    int height = surfaceHeight(tile, blockX, blockZ);
                    for (int y = 0; y < volume.sizeY(); y++) {
                        float value = this.output == Output.HEIGHT ? height : height - volume.blockY(y);
                        outputBuffer.set(volume.indexUnchecked(x, y, z), value);
                    }
                }
            }
        }
    }

    /** The heightmap tile a column falls in (kept while consecutive columns stay in it). */
    private static final class Tile {
        int blockStartX = Integer.MIN_VALUE, blockStartZ = Integer.MIN_VALUE, blockEndX = Integer.MIN_VALUE, blockEndZ = Integer.MIN_VALUE;
        HeightmapData data;

        void update(int x, int z) {
            if (x < this.blockStartX || x >= this.blockEndX || z < this.blockStartZ || z >= this.blockEndZ) {
                int tileSize = TerrainDiffusionConfig.tileSize();
                int tileShift = Integer.numberOfTrailingZeros(tileSize);
                this.blockStartX = (x >> tileShift) << tileShift;
                this.blockStartZ = (z >> tileShift) << tileShift;
                this.blockEndX = this.blockStartX + tileSize;
                this.blockEndZ = this.blockStartZ + tileSize;
                this.data = LocalTerrainProvider.getInstance().fetchHeightmap(this.blockStartZ, this.blockStartX, this.blockEndZ, this.blockEndX);
            }
        }
    }
}
