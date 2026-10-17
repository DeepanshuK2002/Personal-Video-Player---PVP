import { ApplicationSettings } from '@nativescript/core';
import { describe, expect, it } from 'vitest';
import { SETTINGS_SYNC_SERVICES } from '~/utils/constants';
import { BaseSyncService, getStoredSyncServices } from './BaseSyncService';
import { SyncTypes } from './types';

// Sync service configuration is persisted as a JSON blob under a settings key
// that cannot be renamed without losing every user's configured services.

function storeServices(services: unknown[]) {
    ApplicationSettings.setString(SETTINGS_SYNC_SERVICES, JSON.stringify(services));
}

class TestSyncService extends BaseSyncService {
    type = SyncTypes.webdav_data;
    syncMask = 1;
    stop() {}
    shouldSync() {
        return true;
    }
}

describe('getStoredSyncServices', () => {
    it('returns an empty list when nothing has been configured', () => {
        expect(getStoredSyncServices()).toEqual([]);
    });

    it('reads back the services that were stored', () => {
        const services = [{ id: 1, type: SyncTypes.webdav_data, enabled: true, syncFolders: [3] }];
        storeServices(services);
        expect(getStoredSyncServices()).toEqual(services);
    });

    it('preserves the folder filter across a store/read round-trip', () => {
        storeServices([{ id: 7, type: SyncTypes.gdrive_pdf, syncFolders: [1, 2] }]);
        expect(getStoredSyncServices()[0].syncFolders).toEqual([1, 2]);
    });

    it('reads from the settings key that must stay stable for existing users', () => {
        storeServices([{ id: 1, type: SyncTypes.webdav_data }]);
        expect(SETTINGS_SYNC_SERVICES).toBe('sync_services');
    });
});

describe('BaseSyncService.updateSettings', () => {
    it('applies the update to the instance', () => {
        const service = new TestSyncService();
        service.id = 42;
        storeServices([{ id: 42, type: SyncTypes.webdav_data, autoSync: false }]);

        service.updateSettings({ autoSync: true });

        expect(service.autoSync).toBe(true);
    });

    it('persists the update to the stored services', () => {
        const service = new TestSyncService();
        service.id = 42;
        storeServices([{ id: 42, type: SyncTypes.webdav_data, autoSync: false }]);

        service.updateSettings({ autoSync: true, syncFolders: [5] });

        const [stored] = getStoredSyncServices();
        expect(stored.autoSync).toBe(true);
        expect(stored.syncFolders).toEqual([5]);
    });

    it('only updates the matching service', () => {
        const service = new TestSyncService();
        service.id = 42;
        storeServices([
            { id: 41, type: SyncTypes.gdrive_pdf, autoSync: false },
            { id: 42, type: SyncTypes.webdav_data, autoSync: false }
        ]);

        service.updateSettings({ autoSync: true });

        const stored = getStoredSyncServices();
        expect(stored.find((entry) => entry.id === 41).autoSync).toBe(false);
        expect(stored.find((entry) => entry.id === 42).autoSync).toBe(true);
    });

    it('still applies the change in memory when the service is not stored yet', () => {
        const service = new TestSyncService();
        service.id = 99;
        storeServices([{ id: 42, type: SyncTypes.webdav_data }]);

        service.updateSettings({ autoSync: true });

        expect(service.autoSync).toBe(true);
        expect(getStoredSyncServices()).toHaveLength(1);
    });
});

describe('BaseSyncService instance registry', () => {
    it('returns the same singleton for repeated getOrCreateInstance calls', () => {
        const first = TestSyncService.getOrCreateInstance();
        const second = TestSyncService.getOrCreateInstance();
        expect(second).toBe(first);
        TestSyncService.destroyInstance();
    });

    it('forgets the instance after destroyInstance', () => {
        const first = TestSyncService.getOrCreateInstance();
        TestSyncService.destroyInstance();
        expect(TestSyncService.getInstance()).toBeUndefined();
        expect(TestSyncService.getOrCreateInstance()).not.toBe(first);
        TestSyncService.destroyInstance();
    });

    it('defaults a new service to enabled and manual sync', () => {
        const service = new TestSyncService();
        expect(service.enabled).toBe(true);
        expect(service.autoSync).toBe(false);
    });

    it('leaves syncFolders unset so a new service syncs every folder', () => {
        expect(new TestSyncService().syncFolders).toBeUndefined();
    });
});
