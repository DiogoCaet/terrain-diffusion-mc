package com.github.xandergos.terraindiffusionmc.mixin.client;

import com.github.xandergos.terraindiffusionmc.client.WorldScaleSettingsScreen;
import net.minecraft.client.gui.screens.worldselection.PresetEditor;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.levelgen.presets.WorldPreset;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Gives the Terrain Diffusion world type a "Customize" screen (the world scale), the way vanilla
 * gives one to superflat worlds. 26.3 port: replaces the 1.21 mixin on CreateWorldScreen's World
 * tab lambdas; the button is enabled whenever the selected preset has a {@link PresetEditor}.
 */
@Mixin(WorldCreationUiState.class)
public abstract class WorldCreationUiStateMixin {
    private static final ResourceKey<WorldPreset> TERRAIN_DIFFUSION_PRESET_KEY =
            ResourceKey.create(Registries.WORLD_PRESET, Identifier.fromNamespaceAndPath("terrain-diffusion-mc", "terrain_diffusion"));
    private static final PresetEditor SCALE_EDITOR = (parent, settings) -> new WorldScaleSettingsScreen(parent);

    @Shadow
    public abstract WorldCreationUiState.WorldTypeEntry getWorldType();

    @Inject(method = "getPresetEditor", at = @At("HEAD"), cancellable = true)
    private void terrainDiffusionMc$scaleEditor(CallbackInfoReturnable<PresetEditor> cir) {
        Holder<WorldPreset> preset = this.getWorldType().preset();
        if (preset != null && preset.is(TERRAIN_DIFFUSION_PRESET_KEY)) {
            cir.setReturnValue(SCALE_EDITOR);
        }
    }
}
