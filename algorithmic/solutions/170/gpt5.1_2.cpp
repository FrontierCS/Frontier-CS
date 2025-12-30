#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 100;

int N, L;
int T[MAXN];
long long weightPrefix[MAXN];

struct XorShift {
    uint32_t x, y, z, w;
    XorShift() {
        x = 123456789u;
        y = 362436069u;
        z = 521288629u;
        w = 88675123u;
    }
    inline uint32_t next() {
        uint32_t t = x ^ (x << 11);
        x = y; y = z; z = w;
        w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
        return w;
    }
    inline int nextInt(int l, int r) {
        return l + (int)(next() % (uint32_t)(r - l + 1));
    }
};

inline int weightedRandom(XorShift &rng) {
    long long total = weightPrefix[N - 1];
    uint32_t r = rng.next();
    long long x = (long long)(r % (uint32_t)total);
    int low = 0, high = N - 1;
    while (low < high) {
        int mid = (low + high) >> 1;
        if (weightPrefix[mid] > x) high = mid;
        else low = mid + 1;
    }
    return low;
}

long long simulate(const int a[], const int b[], int cntOut[]) {
    static int used[MAXN];
    memset(cntOut, 0, sizeof(int) * N);
    memset(used, 0, sizeof(int) * N);
    int cur = 0;
    cntOut[0] = 1;
    used[0] = 1;
    for (int step = 2; step <= L; ++step) {
        int t = used[cur];
        int nxt = (t & 1) ? a[cur] : b[cur];
        cur = nxt;
        cntOut[cur]++;
        used[cur]++;
    }
    long long E = 0;
    for (int i = 0; i < N; ++i) {
        E += llabs((long long)cntOut[i] - (long long)T[i]);
    }
    return E;
}

void randomMapping(int a[], int b[], XorShift &rng) {
    for (int i = 0; i < N; ++i) {
        int j1 = weightedRandom(rng);
        int j2 = weightedRandom(rng);
        a[i] = j1;
        b[i] = j2;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> L;
    for (int i = 0; i < N; ++i) cin >> T[i];

    // Precompute weights for initial random mappings
    weightPrefix[0] = (long long)T[0] + 1;
    for (int i = 1; i < N; ++i) {
        weightPrefix[i] = weightPrefix[i - 1] + (long long)T[i] + 1;
    }

    XorShift rng;

    const int RESTARTS = 5;
    const int LS_ITERS = 50;
    const int SIM_BUDGET = 260;

    int usedSims = 0;

    int bestA[MAXN], bestB[MAXN];
    long long bestE = (1LL << 60);

    int curA[MAXN], curB[MAXN];
    int curCnt[MAXN], newCnt[MAXN];

    bool done = false;

    for (int r = 0; r < RESTARTS && usedSims < SIM_BUDGET && !done; ++r) {
        // Random initial mapping
        randomMapping(curA, curB, rng);
        long long curE = simulate(curA, curB, curCnt);
        ++usedSims;

        if (curE < bestE) {
            bestE = curE;
            memcpy(bestA, curA, sizeof(int) * N);
            memcpy(bestB, curB, sizeof(int) * N);
            if (bestE == 0) {
                done = true;
                break;
            }
        }

        // Local search
        for (int it = 0; it < LS_ITERS && usedSims < SIM_BUDGET && !done; ++it) {
            int oversIdx[MAXN], defIdx[MAXN];
            int oversCnt = 0, defCnt = 0;

            for (int i = 0; i < N; ++i) {
                int diff = curCnt[i] - T[i];
                if (diff > 0) {
                    oversIdx[oversCnt++] = i;
                } else if (diff < 0) {
                    defIdx[defCnt++] = i;
                }
            }

            if (oversCnt == 0 || defCnt == 0) break;

            int u = oversIdx[rng.nextInt(0, oversCnt - 1)];
            int v = defIdx[rng.nextInt(0, defCnt - 1)];

            int which = (int)(rng.next() & 1u);
            int *edgePtr = (which == 0 ? &curA[u] : &curB[u]);
            if (*edgePtr == v) continue; // no effective change

            int old = *edgePtr;
            *edgePtr = v;

            long long newE = simulate(curA, curB, newCnt);
            ++usedSims;

            if (newE <= curE) {
                curE = newE;
                memcpy(curCnt, newCnt, sizeof(int) * N);
                if (newE < bestE) {
                    bestE = newE;
                    memcpy(bestA, curA, sizeof(int) * N);
                    memcpy(bestB, curB, sizeof(int) * N);
                    if (bestE == 0) {
                        done = true;
                        break;
                    }
                }
            } else {
                *edgePtr = old; // revert
            }
        }
    }

    // Output best found mapping
    for (int i = 0; i < N; ++i) {
        cout << bestA[i] << ' ' << bestB[i] << '\n';
    }

    return 0;
}