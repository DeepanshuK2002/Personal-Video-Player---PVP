<script lang="ts">
    import { openUrl } from '@nativescript/core/utils';
    import { showBottomSheet } from '@nativescript-community/ui-material-bottomsheet/svelte';
    import { navigate } from '@shared/utils/svelte/ui';
    import { colors, windowInset } from '~/variables';
    import HeroIcon from './HeroIcon.svelte';
    import HeroIconButton from './HeroIconButton.svelte';

    let { colorBackground, colorOnBackground, colorOnSurfaceVariant, colorOutline, colorPrimary } = $colors;
    $: ({ colorBackground, colorOnBackground, colorOnSurfaceVariant, colorOutline, colorPrimary } = $colors);

    export let onClose: () => void = () => {};

    async function onItemTap(id: string) {
        onClose();
        switch (id) {
            case 'settings': {
                const Settings = (await import('~/components/settings/Settings.svelte')).default;
                navigate({ page: Settings });
                break;
            }
            case 'sync': {
                const DataSyncSettings = (await import('~/components/settings/sync/DataSyncSettings.svelte')).default;
                navigate({ page: DataSyncSettings });
                break;
            }
            case 'backup': {
                const Settings = (await import('~/components/settings/Settings.svelte')).default;
                navigate({ page: Settings });
                break;
            }
            case 'trash': {
                const TrashList = (await import('~/components/list/TrashList.svelte')).default;
                navigate({ page: TrashList });
                break;
            }
            case 'tutorial': {
                openUrl('https://github.com/KOLS-Co/CleanScanner#readme');
                break;
            }
            case 'rate': {
                try {
                    if (__ANDROID__) {
                        openUrl(`market://details?id=${__APP_ID__}`);
                    } else {
                        openUrl(`https://apps.apple.com/app/id${__APP_ID__}`);
                    }
                } catch {
                    openUrl(`https://play.google.com/store/apps/details?id=${__APP_ID__}`);
                }
                break;
            }
            case 'feedback': {
                openUrl('https://github.com/KOLS-Co/CleanScanner/issues');
                break;
            }
            case 'about': {
                const ThirdParty = (await import('~/components/settings/ThirdPartySoftwareBottomSheet.svelte')).default;
                showBottomSheet({ skipCollapsedState: true, view: ThirdParty });
                break;
            }
        }
    }
</script>

<gridlayout backgroundColor={colorBackground} columns="*" height="100%" rows="auto,auto,*" width="100%">
    <!-- Header -->
    <gridlayout
        columns="*,auto"
        height={56 + $windowInset.top}
        paddingBottom={10}
        paddingLeft={24}
        paddingRight={16}
        paddingTop={$windowInset.top + 10}
        row={0}
        verticalAlignment="center"
    >
        <stacklayout orientation="horizontal" verticalAlignment="center">
            <label color={colorOnBackground} fontSize={22} fontWeight="bold" text="Clean " verticalAlignment="center" />
            <label color={colorPrimary} fontSize={22} fontWeight="bold" text="Scanner" verticalAlignment="center" />
        </stacklayout>
        <HeroIconButton
            col={1}
            buttonHeight={44}
            buttonWidth={44}
            horizontalAlignment="right"
            iconColor={colorOnSurfaceVariant}
            name="x-mark"
            rippleColor={colorOutline}
            size={24}
            verticalAlignment="center"
            on:tap={onClose}
        />
    </gridlayout>

    <!-- Header Full-Width Divider -->
    <stacklayout backgroundColor={colorOutline} height={1} row={1} width="100%" />

    <!-- Content Items List -->
    <scrollview row={2}>
        <stacklayout paddingBottom={$windowInset.bottom + 20} paddingLeft={24} paddingRight={24} paddingTop={12}>
            <!-- Setting -->
            <gridlayout
                columns="28,*"
                height={50}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('settings')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="wrench-screwdriver" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="Setting" verticalTextAlignment="center" />
            </gridlayout>

            <!-- Divider 1 -->
            <stacklayout backgroundColor={colorOutline} height={1} marginBottom={10} marginTop={10} />

            <!-- Sync to Cloud -->
            <gridlayout
                columns="28,*"
                height={50}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('sync')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="cloud" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="Sync to Cloud" verticalTextAlignment="center" />
            </gridlayout>

            <!-- Backup file / Restore -->
            <gridlayout
                columns="28,*"
                height={50}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('backup')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="arrow-path" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="Backup file / Restore" verticalTextAlignment="center" />
            </gridlayout>

            <!-- Trash -->
            <gridlayout
                columns="28,*"
                height={50}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('trash')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="trash" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="Trash" verticalTextAlignment="center" />
            </gridlayout>

            <!-- Divider 2 -->
            <stacklayout backgroundColor={colorOutline} height={1} marginBottom={10} marginTop={10} />

            <!-- Tutorial -->
            <gridlayout
                columns="28,*"
                height={50}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('tutorial')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="question-mark-circle" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="Tutorial" verticalTextAlignment="center" />
            </gridlayout>

            <!-- I love this app! -->
            <gridlayout
                columns="28,*"
                height={50}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('rate')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="hand-thumb-up" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="I love this app!" verticalTextAlignment="center" />
            </gridlayout>

            <!-- Feature Request/ Bug Report -->
            <gridlayout
                columns="28,*"
                minHeight={50}
                paddingBottom={6}
                paddingTop={6}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('feedback')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="chat-bubble-bottom-center-text" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="Feature Request/ Bug Report" textWrap={true} verticalTextAlignment="center" />
            </gridlayout>

            <!-- About CleanScanner -->
            <gridlayout
                columns="28,*"
                height={50}
                rippleColor={colorOutline}
                verticalAlignment="center"
                on:tap={() => onItemTap('about')}
            >
                <HeroIcon col={0} color={colorOnSurfaceVariant} name="information-circle" size={24} verticalAlignment="center" />
                <label col={1} color={colorOnBackground} fontSize={16} fontWeight="400" marginLeft={18} text="About CleanScanner" verticalTextAlignment="center" />
            </gridlayout>
        </stacklayout>
    </scrollview>
</gridlayout>
