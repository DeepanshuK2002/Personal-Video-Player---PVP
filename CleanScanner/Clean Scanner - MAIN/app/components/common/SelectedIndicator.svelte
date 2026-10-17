<script lang="ts">
    import HeroIcon from '~/components/common/HeroIcon.svelte';
    export let selected: boolean = false;
    export let size: number = 22;
    export let color: string = '#32bf84';
</script>

<gridlayout
    backgroundColor={color}
    borderRadius={size / 2}
    elevation={2}
    height={size}
    horizontalAlignment="right"
    margin={8}
    verticalAlignment="top"
    visibility={selected ? 'visible' : 'hidden'}
    width={size}
    {...$$restProps}
>
    <HeroIcon color="#ffffff" name="check" size={Math.round(size * 0.7)} strokeWidth={2.5} />
</gridlayout>
