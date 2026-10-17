<script lang="ts">
    import { NativeViewElementNode } from '@nativescript-community/svelte-native/dom';
    import { Page } from '@nativescript/core';
    import { closeModal } from '@shared/utils/svelte/ui';
    import CropView from '~/components/common/CropView.svelte';
    import HeroIcon from '~/components/common/HeroIcon.svelte';
    import { lc } from '~/helpers/locale';
    import { ImportImageData } from '~/models/OCRDocument';
    import { colors, windowInset } from '~/variables';

    let page: NativeViewElementNode<Page>;
    let cropView: CropView;

    export let cropItem: ImportImageData;
    export let quad;
    export let quadChanged = false;
    let quads;
    $: quads = quad ? [quad] : [];

    function onRecropTapFinish() {
        closeModal(quadChanged ? quads[0] : undefined);
    }

    function onCancel() {
        closeModal();
    }

    function resetCrop() {
        const shouldInverse = cropItem.imageRotation % 180 !== 0;
        const imageWidth = shouldInverse ? cropItem.imageHeight : cropItem.imageWidth;
        const imageHeight = shouldInverse ? cropItem.imageWidth : cropItem.imageHeight;
        quad = [
            [0, 0],
            [imageWidth - 0, 0],
            [imageWidth - 0, imageHeight - 0],
            [0, imageHeight - 0]
        ];
        quadChanged = true;
    }

    function rotateLeft() {
        cropItem.imageRotation = (cropItem.imageRotation + 270) % 360;
        cropItem = cropItem;
        resetCrop();
    }

    function rotateRight() {
        cropItem.imageRotation = (cropItem.imageRotation + 90) % 360;
        cropItem = cropItem;
        resetCrop();
    }

    async function onUndo() {
        cropView?.applyUndo();
    }

    async function onUndosChanged() {
        cropItem = cropItem;
    }
</script>

<page bind:this={page} id="modalImport" actionBarHidden={true} statusBarStyle="dark">
    <gridlayout class="pageContent" backgroundColor="#111827" rows="auto,*,auto">
        <!-- Top bar matching camera.png: Cancel on left, Border adjustment title in center -->
        <gridlayout
            columns="auto,*,auto"
            padding="0 16"
            paddingTop={$windowInset.top + 8}
            row={0}
            verticalAlignment="top"
        >
            <label
                color="#E5E7EB"
                fontSize={16}
                fontWeight="500"
                padding="8 4"
                text={lc('cancel')}
                verticalAlignment="center"
                on:tap={onCancel}
            />
            <label
                col={1}
                color="white"
                fontSize={17}
                fontWeight="600"
                text="Border adjustment"
                textAlignment="center"
                verticalAlignment="center"
            />
            <!-- Empty placeholder to balance Cancel button -->
            <label col={2} opacity={0} padding="8 4" text={lc('cancel')} />
        </gridlayout>

        <!-- Viewfinder / CropView in center -->
        <CropView
            bind:this={cropView}
            {...cropItem ? cropItem : null}
            bind:quadChanged
            bind:quads
            row={1}
            on:undosChanged={onUndosChanged}
        />

        <!-- Bottom toolbar matching camera.png: Reset, Detect, Rotate L, Rotate R, Checkmark -->
        <gridlayout
            backgroundColor="#1F2937"
            borderRadius="24 24 0 0"
            elevation={8}
            paddingBottom={$windowInset.bottom + 12}
            paddingLeft={16}
            paddingRight={16}
            paddingTop={14}
            row={2}
        >
            <flexlayout alignItems="center" justifyContent="space-around" width="100%">
                <!-- Full Crop / Reset -->
                <gridlayout
                    borderRadius={22}
                    height={46}
                    rippleColor="#32bf84"
                    width={46}
                    on:tap={resetCrop}
                >
                    <HeroIcon color="#D1D5DB" name="arrows-pointing-out" size={24} />
                </gridlayout>

                <!-- Undo / Auto Detect -->
                <gridlayout
                    borderRadius={22}
                    height={46}
                    rippleColor="#32bf84"
                    width={46}
                    on:tap={onUndo}
                >
                    <HeroIcon color="#D1D5DB" name="viewfinder-circle" size={24} />
                </gridlayout>

                <!-- Rotate Left -->
                <gridlayout
                    borderRadius={22}
                    height={46}
                    rippleColor="#32bf84"
                    width={46}
                    on:tap={rotateLeft}
                >
                    <HeroIcon color="#D1D5DB" name="arrow-uturn-left" size={24} />
                </gridlayout>

                <!-- Rotate Right -->
                <gridlayout
                    borderRadius={22}
                    height={46}
                    rippleColor="#32bf84"
                    width={46}
                    on:tap={rotateRight}
                >
                    <HeroIcon color="#D1D5DB" name="arrow-uturn-right" size={24} />
                </gridlayout>

                <!-- Checkmark / Done (green highlight) -->
                <gridlayout
                    backgroundColor="#32bf84"
                    borderRadius={23}
                    elevation={4}
                    height={46}
                    rippleColor="#ffffff"
                    width={46}
                    on:tap={onRecropTapFinish}
                >
                    <HeroIcon color="#ffffff" name="check" size={24} strokeWidth={2.5} />
                </gridlayout>
            </flexlayout>
        </gridlayout>
    </gridlayout>
</page>
