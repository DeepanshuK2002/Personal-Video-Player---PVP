<script context="module" lang="ts">
    import { lc } from '@nativescript-community/l';
    import { createNativeAttributedString } from '@nativescript-community/text';
    import { LayoutAlignment, Paint, StaticLayout } from '@nativescript-community/ui-canvas';
    import { CollectionView } from '@nativescript-community/ui-collectionview';
    import { AndroidActivityResultEventData, Application, ObservableArray, StackLayout, Utils } from '@nativescript/core';
    import { openFile, openUrl, throttle } from '@nativescript/core/utils';
    import { showError } from '@shared/utils/showError';
    import dayjs from 'dayjs';
    import { Template } from '@nativescript-community/svelte-native/components';
    import { NativeViewElementNode } from '@nativescript-community/svelte-native/dom';
    import { isEInk } from '~/helpers/theme';
    import { DocFolder } from '~/models/OCRDocument';
    import { formatStorageSizes, importImageFromCamera } from '~/utils/ui';
    import { computeStorageSizes } from '~/utils/originals';
    import { colors, fontScale, hasCamera, windowInset } from '~/variables';
    import PageIndicator from '../common/PageIndicator.svelte';
    import RotableImageView from '../common/RotableImageView.svelte';
    import SelectedIndicator from '../common/SelectedIndicator.svelte';
    import SyncIndicator from '../common/SyncIndicator.svelte';
    import MainList, { Item } from './MainList.svelte';
    import { ellipsize } from '~/utils/utils.common';
    import FavoriteIndicator from '~/components/common/FavoriteIndicator.svelte';
    import HeroIcon from '../common/HeroIcon.svelte';

    const textPaint = new Paint();
    const IMAGE_DECODE_WIDTH = Utils.layout.toDevicePixels(200);
</script>

<script lang="ts">
    let { colorBackground, colorOnBackground, colorOnSurfaceVariant, colorOutline, colorPrimary, colorPrimaryContainer, colorSurface } = $colors;
    $: ({ colorBackground, colorOnBackground, colorOnSurfaceVariant, colorOutline, colorPrimary, colorPrimaryContainer, colorSurface } = $colors);
    export let title = lc('documents');
    export let folder: DocFolder;
    let fabHolder: NativeViewElementNode<StackLayout>;
    let collectionView: NativeViewElementNode<CollectionView>;
    let viewStyle: string;
    let syncEnabled: boolean;
    let nbSelected: number = 0;
    let folderItems: ObservableArray<Item>;
    let documents: ObservableArray<Item>;
    let getSyncColors: (item: Item) => string[];
    let onItemLongPress: (item: Item, event?) => Promise<void>;
    let onItemTap: (item: Item) => Promise<void>;
    let importImages: () => Promise<void>;
    let importDocument: (importPDFs?: boolean) => Promise<void>;
    let refreshCollectionView: () => void;

    $: condensed = viewStyle === 'condensed';
    function getItemRowHeight(viewStyle) {
        return condensed ? 80 : 150;
    }
    function getImageMargin(viewStyle) {
        return 10;
    }
    function getItemImageHeight(viewStyle) {
        return condensed ? 44 : 94;
    }

    $: textPaint.color = colorOnBackground || 'black';

    function onCanvasDraw(item: Item, { canvas, object }: { canvas: Canvas; object: CanvasView }) {
        const w = canvas.getWidth();
        const h = canvas.getHeight();
        const dx = 10 + getItemImageHeight(viewStyle) * $fontScale + 16;
        textPaint.color = colorOnSurfaceVariant;
        const { doc } = item;
        textPaint.textSize = condensed ? 11 : 14 * $fontScale;
        canvas.drawText(formatStorageSizes(computeStorageSizes(doc.pages)), dx, h - (condensed ? 0 : 16) - 10, textPaint);
        textPaint.color = colorOnBackground;
        const topText = createNativeAttributedString({
            spans: [
                {
                    fontSize: 16 * $fontScale,
                    fontWeight: 'bold',
                    lineBreak: 'end',
                    lineHeight: 18 * $fontScale,
                    text: ellipsize(doc.name, 50)
                },
                {
                    color: colorOnSurfaceVariant,
                    fontSize: 13 * $fontScale,
                    lineHeight: condensed ? 14 : 20 * $fontScale,
                    text: '\n' + dayjs(doc.createdDate).format('MMM D, YYYY h:mma') + ' | ' + (doc.pages.length === 1 ? '1 page' : `${doc.pages.length} pages`)
                }
            ]
        });
        const staticLayout = new StaticLayout(topText, textPaint, Math.max(0, w - dx), LayoutAlignment.ALIGN_NORMAL, 1, 0, true);
        canvas.translate(dx, (condensed ? 0 : 10) + 10);
        staticLayout.draw(canvas);
    }

    async function onStartCam(inverseUseSystemCamera = false) {
        try {
            await importImageFromCamera({ folder, inverseUseSystemCamera });
        } catch (error) {
            showError(error);
        }
    }
</script>

<MainList
    folderViewStyles={{
        horizontal: { name: lc('horizontal') },
        vertical: { name: lc('vertical') }
    }}
    {title}
    viewStyles={{
        default: { name: lc('expanded') },
        condensed: { name: lc('condensed') }
    }}
    bind:fabHolder
    bind:viewStyle
    bind:onItemTap
    bind:onItemLongPress
    bind:syncEnabled
    bind:folder
    bind:nbSelected
    bind:importDocument
    bind:importImages
    bind:refreshCollectionView
    bind:getSyncColors
    bind:documents
    bind:folderItems
    bind:collectionView
>
    <Template let:item>
        <canvasview
            class="card"
            borderWidth={isEInk ? 1 : 0}
            height={getItemRowHeight(viewStyle) * $fontScale}
            on:tap={() => onItemTap(item)}
            on:longPress={(e) => onItemLongPress(item, e)}
            on:draw={(e) => onCanvasDraw(item, e)}
        >
            <RotableImageView
                id="imageView"
                borderRadius={12}
                decodeWidth={IMAGE_DECODE_WIDTH}
                horizontalAlignment="left"
                item={item.doc.pages[0]}
                marginBottom={getImageMargin(viewStyle)}
                marginLeft={10}
                marginTop={getImageMargin(viewStyle)}
                sharedTransitionTag={`document_${item.doc.id}_${item.doc.pages[0]?.id}`}
                stretch="aspectFill"
                width={getItemImageHeight(viewStyle) * $fontScale}
            />
            <SelectedIndicator horizontalAlignment="left" margin={10} selected={item.selected} />
            <SyncIndicator syncColors={getSyncColors(item)} visible={syncEnabled} />
            <PageIndicator horizontalAlignment="right" margin={10} scale={$fontScale} text={item.doc.pages.length} />
            <FavoriteIndicator favorite={item.doc.favorite === 1} />
        </canvasview>
    </Template>

    <gridlayout
        bind:this={fabHolder}
        slot="fab"
        backgroundColor={colorSurface || '#FFFFFF'}
        borderColor={colorOutline || '#E5E7EB'}
        borderRadius={28}
        borderWidth={1}
        columns="auto,auto,auto"
        elevation={4}
        height={56}
        horizontalAlignment="right"
        marginBottom={Math.max(24, $windowInset.bottom + 12)}
        marginRight={20}
        paddingLeft={12}
        paddingRight={12}
        row={2}
        verticalAlignment="bottom"
    >
        <gridlayout
            col={0}
            height={44}
            rippleColor={colorPrimaryContainer || '#CAFFFB'}
            verticalAlignment="center"
            width={44}
            on:tap={throttle(() => importImages(), 500)}
        >
            <HeroIcon color={colorPrimary || '#048243'} name="photo" size={24} verticalAlignment="center" horizontalAlignment="center" />
        </gridlayout>
        {#if $hasCamera}
            <stacklayout backgroundColor={colorOutline || '#E5E7EB'} col={1} height={24} margin="0 6" verticalAlignment="center" width={1} />
            <gridlayout
                col={2}
                height={44}
                rippleColor={colorPrimaryContainer || '#CAFFFB'}
                verticalAlignment="center"
                width={44}
                on:tap={throttle(() => onStartCam(), 500)}
                on:longPress={() => onStartCam(true)}
            >
                <HeroIcon color={colorPrimary || '#048243'} name="camera" size={24} verticalAlignment="center" horizontalAlignment="center" />
            </gridlayout>
        {/if}
    </gridlayout>
</MainList>
