<script lang="ts">
    import { getHeroIcon } from '~/utils/heroicons';

    export let name: string;
    export let type: 'outline' | 'solid' = 'outline';
    export let size: number = 24;
    export let color: string = '#111827';
    export let strokeWidth: number = 1.5;

    $: svg = getHeroIcon(name, type, color, strokeWidth);
</script>

<svgview
    height={size}
    src={svg}
    stretch="aspectFit"
    width={size}
    {...$$restProps}
    on:tap
/>
