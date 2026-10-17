<script lang="ts">
    import { CoreTypes, Frame } from '@nativescript/core';
    import { showError } from '@shared/utils/showError';
    import { closeModal, conditionalEvent, fade, goBack } from '@shared/utils/svelte/ui';
    import { onMount } from 'svelte';
    import { colors, windowInset } from '~/variables';
    import HeroIconButton from './HeroIconButton.svelte';

    let { colorOnBackground } = $colors;
    $: ({ colorOnBackground } = $colors);

    export let title: string = null;
    export let showMenuIcon: boolean = false;
    export let canGoBack: boolean = false;
    export let forceCanGoBack: boolean = false;
    export let modalWindow: boolean = false;
    export let disableBackButton: boolean = false;
    export let buttonsDefaultVisualState = null;
    export let clazz: string = '';
    export let onGoBack: Function = null;
    export let onTitleTap: Function = null;
    export let onMenuTap: Function = null;
    export let centerTitle: boolean = false;
    let heroIconName = 'bars-3';
    let menuIconVisible: boolean = false;
    let menuIconVisibility: CoreTypes.VisibilityType;
    let paddingLeft = 16;

    onMount(() => {
        if (!canGoBack) {
            const frame = Frame.topmost();
            canGoBack = frame?.canGoBack() ?? false;
        }
    });
    function onMenuIcon() {
        try {
            if (modalWindow) {
                if (onGoBack) {
                    onGoBack();
                } else {
                    closeModal(undefined);
                }
            } else if (forceCanGoBack || canGoBack) {
                if (onGoBack) {
                    onGoBack();
                } else {
                    goBack();
                }
            } else if (onMenuTap) {
                onMenuTap();
            } else if (onGoBack) {
                onGoBack();
            }
        } catch (error) {
            showError(error);
        }
    }
    $: {
        if (modalWindow) {
            heroIconName = 'x-mark';
        } else if (forceCanGoBack || canGoBack) {
            heroIconName = __IOS__ ? 'chevron-left' : 'arrow-left';
        } else {
            heroIconName = 'bars-3';
        }
    }
    $: menuIconVisible = ((forceCanGoBack || canGoBack || modalWindow) && !disableBackButton) || showMenuIcon || !!onMenuTap;
    $: menuIconVisibility = menuIconVisible ? 'visible' : 'collapse';
    $: paddingLeft = menuIconVisible ? 0 : 16;
</script>

<gridlayout class={'actionBar ' + clazz} columns="auto,*, auto" paddingLeft={4} paddingRight={4} rows="*" {...$$restProps} transition:fade={{ duration: 300 }} android:marginTop={$windowInset.top}>
    {#if centerTitle}
        <label
            class={'actionBarTitle ' + clazz}
            autoFontSize={true}
            col={0}
            colSpan={3}
            color={colorOnBackground}
            fontSize={20}
            fontWeight="600"
            horizontalAlignment="center"
            lineBreak="end"
            maxLines={1}
            text={title || ''}
            textAlignment="center"
            verticalTextAlignment="center"
            visibility={!!title ? 'visible' : 'hidden'}
            {...$$restProps?.titleProps}
            use:conditionalEvent={{ condition: !!onTitleTap, event: 'tap', callback: onTitleTap }}
        />
    {:else}
        <label
            class={'actionBarTitle ' + clazz}
            autoFontSize={true}
            col={1}
            lineBreak="end"
            maxLines={2}
            paddingLeft={menuIconVisible ? 0 : 16}
            text={title || ''}
            textAlignment="left"
            verticalTextAlignment="center"
            visibility={!!title ? 'visible' : 'hidden'}
            {...$$restProps?.titleProps}
            use:conditionalEvent={{ condition: !!onTitleTap, event: 'tap', callback: onTitleTap }}
        />
    {/if}
    <stacklayout col={0} orientation="horizontal">
        <slot name="left" />
        {#if menuIconVisible}
            <HeroIconButton
                borderRadius={20}
                buttonHeight={44}
                buttonWidth={44}
                iconColor={buttonsDefaultVisualState === 'white' ? '#FFFFFF' : colorOnBackground}
                name={heroIconName}
                size={22}
                on:tap={onMenuIcon}
            />
        {/if}
    </stacklayout>
    <stacklayout col={2} orientation="horizontal">
        <slot />
    </stacklayout>
    <slot name="center" col={1} />
</gridlayout>
