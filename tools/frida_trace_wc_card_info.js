'use strict';

console.log('[wc-card-info] loaded');

const needles = [
    'GetPlayerCardInfo',
    'TEAM_ASSET_ID',
    'CONFEDERATION_ASSET_ID',
    'NATIONALITY_ASSET_ID'
];

const ranges = Process.enumerateRanges({
    protection: 'r--',
    coalesce: true
});

console.log('[wc-card-info] readable ranges:', ranges.length);

for (const needle of needles) {
    console.log('[wc-card-info] looking for:', needle);

    let count = 0;

    for (const range of ranges) {
        try {
            const hits = Memory.scanSync(
                range.base,
                range.size,
                needle
            );

            for (const hit of hits) {
                count++;

                console.log(
                    '[wc-card-info]',
                    needle,
                    '=>',
                    hit.address,
                    'range',
                    range.base,
                    'size',
                    range.size
                );
            }
        } catch (e) {
            // Sommige ranges kunnen tijdens het scannen veranderen.
        }
    }

    console.log(
        '[wc-card-info]',
        needle,
        'hits:',
        count
    );
}

console.log('[wc-card-info] scan complete');