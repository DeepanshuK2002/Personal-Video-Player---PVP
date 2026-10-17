<script lang="ts">
    import HeroIcon from './HeroIcon.svelte';

    export let name: string;
    export let type: 'outline' | 'solid' = 'outline';
    export let size: number = 24;
    export let iconColor: string = '#111827';
    export let rippleColor: string = '#E5E7EB';
    export let buttonWidth: number = 44;
    export let buttonHeight: number = 44;
    export let borderRadius: number = 22;
    export let strokeWidth: number = 1.5;
    export let isEnabled: boolean = true;
    export let tooltip: string = null;
</script>

<gridlayout
    accessibilityLabel={tooltip}
    borderRadius={borderRadius}
    height={buttonHeight}
    horizontalAlignment="center"
    isUserInteractionEnabled={isEnabled}
    opacity={isEnabled ? 1 : 0.4}
    rippleColor={rippleColor}
    verticalAlignment="center"
    width={buttonWidth}
    {...$$restProps}
    on:tap
>
    <HeroIcon
        color={iconColor}
        horizontalAlignment="center"
        isUserInteractionEnabled={false}
        {name}
        {size}
        {strokeWidth}
        {type}
        verticalAlignment="center"
    />
</gridlayout>
