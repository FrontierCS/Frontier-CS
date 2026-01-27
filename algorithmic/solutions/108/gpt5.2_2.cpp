#include <bits/stdc++.h>
using namespace std;

static const int MAXQ = 30000;

struct RNG {
    uint64_t x;
    RNG() {
        x = chrono::high_resolution_clock::now().time_since_epoch().count();
        x ^= (uint64_t)(uintptr_t)this + 0x9e3779b97f4a7c15ULL;
    }
    uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    int nextInt(int bound) {
        return (int)(nextU64() % (uint64_t)bound);
    }
    int nextDir() { return (nextU64() & 1ULL) ? 1 : -1; }
};

int n, m;
int qcnt = 0;

int query(int ring, int dir) {
    cout << "? " << ring << " " << dir << endl;
    cout.flush();
    int a;
    if (!(cin >> a)) exit(0);
    if (a == -1) exit(0);
    qcnt++;
    if (qcnt > MAXQ) exit(0);
    return a;
}

bool scanFindDecrease(int &a, int &lastRing, int &lastDir) {
    for (int ring = 0; ring < n; ring++) {
        for (int dir : {1, -1}) {
            int a1 = query(ring, dir);
            if (a1 < a) {
                a = a1;
                lastRing = ring;
                lastDir = dir;
                return true;
            }
            int a2 = query(ring, -dir);
            a = a2;
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    int S = n * m;

    RNG rng;

    // Get current display value (uncovered count).
    int a = query(0, 1);
    a = query(0, -1);

    // Phase 1: reach a == 0 (perfect tiling).
    int lastRing = -1, lastDir = 0;
    int noImproveAttempts = 0;

    const int SMALL_THRESH = 40;
    const int RAND_TRIES_BEFORE_SCAN = 250;

    while (a > 0) {
        if (qcnt > MAXQ - 14000) {
            // Leave enough budget for phase 2.
            break;
        }

        if (a <= SMALL_THRESH) {
            if (!scanFindDecrease(a, lastRing, lastDir)) {
                // Escape: accept a random move (even if it increases) to try to exit a local minimum.
                int ring = rng.nextInt(n);
                int dir = rng.nextDir();
                a = query(ring, dir);
                lastRing = -1;
            }
            continue;
        }

        // Continue last successful direction if possible.
        if (lastRing != -1) {
            int a1 = query(lastRing, lastDir);
            if (a1 < a) {
                a = a1;
                noImproveAttempts = 0;
                continue;
            } else {
                int a2 = query(lastRing, -lastDir);
                a = a2;
                lastRing = -1;
            }
        }

        bool improved = false;
        for (int tries = 0; tries < RAND_TRIES_BEFORE_SCAN; tries++) {
            int ring = rng.nextInt(n);
            int d1 = rng.nextDir();
            int d2 = -d1;

            for (int pass = 0; pass < 2; pass++) {
                int dir = (pass == 0 ? d1 : d2);
                int a1 = query(ring, dir);
                if (a1 < a) {
                    a = a1;
                    lastRing = ring;
                    lastDir = dir;
                    improved = true;
                    break;
                } else {
                    int a2 = query(ring, -dir);
                    a = a2;
                }
            }
            if (improved) break;
        }

        if (!improved) {
            noImproveAttempts++;
            if (!scanFindDecrease(a, lastRing, lastDir)) {
                // Escape move.
                int ring = rng.nextInt(n);
                int dir = rng.nextDir();
                a = query(ring, dir);
                lastRing = -1;
            }
            noImproveAttempts = 0;
        }
    }

    // Ensure we actually reached a == 0 before phase 2; otherwise try a final scan.
    while (a > 0) {
        if (!scanFindDecrease(a, lastRing, lastDir)) {
            int ring = rng.nextInt(n);
            int dir = rng.nextDir();
            a = query(ring, dir);
            lastRing = -1;
        }
        if (qcnt > MAXQ - 14000) break;
    }

    // If still not zero, we cannot safely proceed; but attempt to proceed anyway.
    // Phase 2 assumes a == 0.
    if (a != 0) {
        // Try some more aggressive scans.
        for (int rep = 0; rep < 10 && a != 0; rep++) {
            if (!scanFindDecrease(a, lastRing, lastDir)) break;
        }
    }

    vector<int> remaining;
    remaining.reserve(max(0, n - 1));
    for (int i = 1; i < n; i++) remaining.push_back(i);

    vector<int> order;
    order.reserve(max(0, n - 1));

    // Phase 2: discover clockwise order using swaps in tiling state.
    for (int step = 0; step < n - 1; step++) {
        // Rotate ring 0 clockwise by m.
        for (int t = 0; t < m; t++) a = query(0, 1);

        int target = a; // expected m in perfect tiling
        int found = -1;
        int foundIdx = -1;

        for (int idx = 0; idx < (int)remaining.size(); idx++) {
            int cand = remaining[idx];
            int a1 = query(cand, -1);
            if (a1 == target - 1) {
                found = cand;
                foundIdx = idx;
                a = a1;
                break;
            } else {
                int a2 = query(cand, 1);
                a = a2;
            }
        }

        if (found == -1) {
            // Fallback: try all rings except 0.
            for (int cand = 1; cand < n; cand++) {
                int a1 = query(cand, -1);
                if (a1 == target - 1) {
                    found = cand;
                    a = a1;
                    break;
                } else {
                    int a2 = query(cand, 1);
                    a = a2;
                }
            }
        }

        if (found == -1) {
            // Cannot proceed.
            break;
        }

        // Remove from remaining if it was tracked.
        if (foundIdx != -1) remaining.erase(remaining.begin() + foundIdx);

        order.push_back(found);

        // Finish swapping: rotate found counterclockwise total m steps (we already did 1).
        for (int t = 1; t < m; t++) a = query(found, -1);

        // Now should be back to 0 in perfect tiling.
    }

    vector<int> p(n, 0);
    for (int j = 0; j < (int)order.size(); j++) {
        int ring = order[j];
        p[ring] = ((j + 1) * m) % S;
    }

    cout << "!";
    for (int i = 1; i < n; i++) cout << " " << p[i];
    cout << endl;
    cout.flush();
    return 0;
}