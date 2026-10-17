<script lang="ts">
    import { VerticalPosition } from '@nativescript-community/ui-popover';
    import { ObservableArray, Utils, View } from '@nativescript/core';
    import HeroIcon from '~/components/common/HeroIcon.svelte';
    import { lc } from '~/helpers/locale';
    import { showPopoverMenu } from '~/utils/ui';
    import { colors, windowInset } from '~/variables';
    import { OptionType } from '@shared/components/OptionSelect.svelte';
    import { slide } from '@shared/utils/svelte/ui';

    export let options: OptionType[] | ObservableArray<OptionType> = [];
    export let onAction: (event, option: OptionType) => void | Promise<void> = null;

    let visibleOptions: OptionType[] = [];
    let overflowOptions: OptionType[] = [];
    let hasOverflow = false;

    $: ({ colorBackground, colorError, colorOnSurface, colorOnSurfaceVariant, colorSurface } = $colors);

    function mapToHeroIcon(option: OptionType): string {
        if (option['heroicon']) return option['heroicon'];
        const id = option.id;
        const icon = option.icon || '';
        if (id === 'delete' || id === 'delete_permanently' || icon.includes('delete')) return 'trash';
        if (id === 'share' || icon.includes('share')) return 'share';
        if (id === 'pdf' || icon.includes('pdf')) return 'document-text';
        if (id === 'transform' || icon.includes('auto-fix')) return 'rectangle-group';
        if (id === 'ocr' || icon.includes('text-recognition')) return 'viewfinder-circle';
        if (id === 'select_all' || icon.includes('select-all')) return 'check';
        if (id === 'move' || id === 'move_folder' || icon.includes('folder')) return 'folder-arrow-down';
        if (id === 'copy' || icon.includes('copy')) return 'document-duplicate';
        if (id === 'rename' || icon.includes('rename')) return 'pencil';
        if (id === 'delete_originals' || icon.includes('remove')) return 'scissors';
        if (id === 'favorite' || icon.includes('star')) return 'sparkles';
        if (id === 'restore' || icon.includes('restore')) return 'arrow-path';
        if (id === 'fullscreen' || icon.includes('fullscreen')) return 'arrows-pointing-out';
        return 'ellipsis-horizontal';
    }

    const MAX_VISIBLE = 6;
    $: {
        const rawOptions = Array.isArray(options) ? options : (options as any)?.elements || [];
        if (rawOptions.length > MAX_VISIBLE) {
            visibleOptions = rawOptions.slice(0, MAX_VISIBLE - 1);
            overflowOptions = rawOptions.slice(MAX_VISIBLE - 1);
            hasOverflow = true;
        } else {
            visibleOptions = rawOptions;
            overflowOptions = [];
            hasOverflow = false;
        }
    }

    async function handleAction(event, option: OptionType) {
        if (onAction) {
            await onAction(event, option);
        }
    }

    async function showMoreOptions(event) {
        const result = await showPopoverMenu({
            anchor: event.object,
            options: new ObservableArray(overflowOptions),
            vertPos: VerticalPosition.ABOVE,
            onClose: async (item) => {
                await handleAction(event, item);
            }
        });
    }
</script>

<gridlayout
    class="selectionToolbar"
    backgroundColor={colorSurface}
    borderColor="#E5E7EB"
    borderRadius="20 20 0 0"
    borderTopWidth={1}
    elevation={8}
    paddingBottom={$windowInset.bottom + 8}
    paddingLeft={8}
    paddingRight={8}
    paddingTop={8}
    rows="auto"
    verticalAlignment="bottom"
    {...$$restProps}
    transition:slide={{ duration: 200 }}
>
    <flexlayout alignItems="center" justifyContent="space-around" width="100%">
        {#each visibleOptions as option}
            {@const color = typeof option.color === 'function' ? option['color'](options) : option.color}
            <stacklayout
                class="selectionItem"
                horizontalAlignment="center"
                padding="6 4"
                rippleColor="#32bf84"
                verticalAlignment="center"
                on:tap={(event) => handleAction(event, option)}
            >
                <HeroIcon
                    color={color || (option.id === 'delete' ? colorError : '#374151')}
                    name={mapToHeroIcon(option)}
                    size={22}
                />
                <label
                    color={color || (option.id === 'delete' ? colorError : '#4B5563')}
                    fontSize={11}
                    fontWeight="500"
                    lineBreak="end"
                    marginTop={4}
                    maxLines={1}
                    text={option.name}
                    textAlignment="center"
                />
            </stacklayout>
        {/each}
        {#if hasOverflow}
            <stacklayout
                class="selectionItem"
                horizontalAlignment="center"
                padding="6 4"
                rippleColor="#32bf84"
                verticalAlignment="center"
                on:tap={showMoreOptions}
            >
                <HeroIcon color="#374151" name="ellipsis-horizontal" size={22} />
                <label
                    color="#4B5563"
                    fontSize={11}
                    fontWeight="500"
                    lineBreak="end"
                    marginTop={4}
                    maxLines={1}
                    text={lc('more')}
                    textAlignment="center"
                />
            </stacklayout>
        {/if}
    </flexlayout>
</gridlayout>
