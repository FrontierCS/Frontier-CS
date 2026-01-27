#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

static inline int64 absDiff(int64 a, int64 b) {
    return (a >= b) ? (a - b) : (b - a);
}

static inline double urand01(std::mt19937_64 &rng) {
    return (rng() >> 11) * (1.0 / 9007199254740992.0); // 2^53
}

struct Entry {
    int64 sum;
    uint32_t mask;
};
static inline bool operator<(const Entry& a, const Entry& b) { return a.sum < b.sum; }

static bool refineMITM(
    const vector<int64>& a, int64 T,
    const vector<int>& selIdx,
    const vector<uint8_t>& baseBits,
    vector<uint8_t>& outBits,
    int64& outSum,
    int64& outErr
) {
    int n = (int)a.size();
    vector<uint8_t> inSel(n, 0);
    for (int idx : selIdx) inSel[idx] = 1;

    int64 fixedSum = 0;
    for (int i = 0; i < n; i++) if (!inSel[i] && baseBits[i]) fixedSum += a[i];

    int64 R = T - fixedSum;

    int m = (int)selIdx.size();
    int h1 = m / 2;
    int h2 = m - h1;

    vector<int64> b1(h1), b2(h2);
    for (int i = 0; i < h1; i++) b1[i] = a[selIdx[i]];
    for (int i = 0; i < h2; i++) b2[i] = a[selIdx[h1 + i]];

    size_t N1 = 1u << h1;
    size_t N2 = 1u << h2;

    vector<int64> sum1(N1, 0), sum2(N2, 0);
    for (size_t mask = 1; mask < N1; mask++) {
        unsigned lsb = __builtin_ctzll(mask);
        sum1[mask] = sum1[mask ^ (1ull << lsb)] + b1[lsb];
    }
    for (size_t mask = 1; mask < N2; mask++) {
        unsigned lsb = __builtin_ctzll(mask);
        sum2[mask] = sum2[mask ^ (1ull << lsb)] + b2[lsb];
    }

    vector<Entry> v1; v1.reserve(N1);
    vector<Entry> v2; v2.reserve(N2);

    for (uint32_t mask = 0; mask < (uint32_t)N1; mask++) v1.push_back({sum1[mask], mask});
    for (uint32_t mask = 0; mask < (uint32_t)N2; mask++) v2.push_back({sum2[mask], mask});

    sort(v2.begin(), v2.end());

    int64 bestSubsetSum = 0;
    uint32_t bestM1 = 0, bestM2 = 0;
    int64 bestErr = LLONG_MAX;

    for (const auto &e1 : v1) {
        int64 target2 = R - e1.sum;
        auto it = lower_bound(v2.begin(), v2.end(), Entry{target2, 0});
        if (it != v2.end()) {
            int64 s = e1.sum + it->sum;
            int64 err = absDiff(s, R);
            if (err < bestErr) {
                bestErr = err; bestSubsetSum = s; bestM1 = e1.mask; bestM2 = it->mask;
                if (bestErr == 0) break;
            }
        }
        if (it != v2.begin()) {
            auto it2 = prev(it);
            int64 s = e1.sum + it2->sum;
            int64 err = absDiff(s, R);
            if (err < bestErr) {
                bestErr = err; bestSubsetSum = s; bestM1 = e1.mask; bestM2 = it2->mask;
            }
        }
    }

    vector<uint8_t> cand = baseBits;
    for (int idx : selIdx) cand[idx] = 0;
    for (int i = 0; i < h1; i++) if (bestM1 & (1u << i)) cand[selIdx[i]] = 1;
    for (int i = 0; i < h2; i++) if (bestM2 & (1u << i)) cand[selIdx[h1 + i]] = 1;

    int64 candSum = fixedSum + bestSubsetSum;
    int64 candErr = absDiff(candSum, T);

    if (candErr < outErr) {
        outBits = std::move(cand);
        outSum = candSum;
        outErr = candErr;
        return true;
    }
    return false;
}

static void greedyInit(const vector<int64>& a, int64 T, vector<uint8_t>& bits, int64& sum) {
    int n = (int)a.size();
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int i, int j) {
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });
    bits.assign(n, 0);
    sum = 0;
    int64 curErr = absDiff(sum, T);
    for (int idx : ord) {
        int64 ns = sum + a[idx];
        int64 nerr = absDiff(ns, T);
        if (nerr <= curErr) {
            bits[idx] = 1;
            sum = ns;
            curErr = nerr;
        }
    }
}

static void randomInit(const vector<int64>& a, std::mt19937_64& rng, vector<uint8_t>& bits, int64& sum) {
    int n = (int)a.size();
    bits.assign(n, 0);
    sum = 0;
    for (int i = 0; i < n; i++) {
        if (rng() & 1ull) {
            bits[i] = 1;
            sum += a[i];
        }
    }
}

static void localImproveAllPairs(const vector<int64>& a, int64 T, vector<uint8_t>& bits, int64& sum) {
    int n = (int)a.size();
    while (true) {
        int64 curErr = absDiff(sum, T);

        int bestI = -1;
        int64 bestSum = sum, bestErr = curErr;

        // best single flip
        for (int i = 0; i < n; i++) {
            int64 ns = sum + (bits[i] ? -a[i] : a[i]);
            int64 err = absDiff(ns, T);
            if (err < bestErr) {
                bestErr = err;
                bestSum = ns;
                bestI = i;
            }
        }
        if (bestI != -1) {
            bits[bestI] ^= 1;
            sum = bestSum;
            if (bestErr == 0) return;
            continue;
        }

        // best pair flip
        int bi = -1, bj = -1;
        bestErr = curErr;
        bestSum = sum;
        for (int i = 0; i < n; i++) {
            int64 di = bits[i] ? -a[i] : a[i];
            for (int j = i + 1; j < n; j++) {
                int64 dj = bits[j] ? -a[j] : a[j];
                int64 ns = sum + di + dj;
                int64 err = absDiff(ns, T);
                if (err < bestErr) {
                    bestErr = err;
                    bestSum = ns;
                    bi = i; bj = j;
                }
            }
        }
        if (bi != -1) {
            bits[bi] ^= 1;
            bits[bj] ^= 1;
            sum = bestSum;
            if (bestErr == 0) return;
            continue;
        }

        break;
    }
}

static void annealRun(
    const vector<int64>& a, int64 T,
    vector<uint8_t> bits, int64 sum,
    int iters, std::mt19937_64& rng,
    vector<uint8_t>& bestBits, int64& bestSum, int64& bestErr
) {
    int n = (int)a.size();
    int64 curErr = absDiff(sum, T);

    if (curErr < bestErr) {
        bestErr = curErr;
        bestSum = sum;
        bestBits = bits;
        if (bestErr == 0) return;
    }

    double temp0 = max(1.0, (double)curErr);
    uniform_int_distribution<int> distIdx(0, n - 1);

    for (int it = 0; it < iters; it++) {
        double t = 1.0 - (double)it / (double)iters;
        double temp = temp0 * t + 1e-9;

        int i = distIdx(rng);
        int64 di = bits[i] ? -a[i] : a[i];

        int64 ns;
        if ((rng() % 100) < 15 && n >= 2) { // 2-flip
            int j = distIdx(rng);
            while (j == i) j = distIdx(rng);
            int64 dj = bits[j] ? -a[j] : a[j];
            ns = sum + di + dj;
            int64 nerr = absDiff(ns, T);
            bool accept = false;
            if (nerr <= curErr) accept = true;
            else {
                double diff = (double)(nerr - curErr);
                double p = exp(-diff / temp);
                if (urand01(rng) < p) accept = true;
            }
            if (accept) {
                bits[i] ^= 1;
                bits[j] ^= 1;
                sum = ns;
                curErr = nerr;
                if (curErr < bestErr) {
                    bestErr = curErr;
                    bestSum = sum;
                    bestBits = bits;
                    if (bestErr == 0) return;
                    temp0 = max(1.0, (double)curErr);
                }
            }
        } else { // 1-flip
            ns = sum + di;
            int64 nerr = absDiff(ns, T);
            bool accept = false;
            if (nerr <= curErr) accept = true;
            else {
                double diff = (double)(nerr - curErr);
                double p = exp(-diff / temp);
                if (urand01(rng) < p) accept = true;
            }
            if (accept) {
                bits[i] ^= 1;
                sum = ns;
                curErr = nerr;
                if (curErr < bestErr) {
                    bestErr = curErr;
                    bestSum = sum;
                    bestBits = bits;
                    if (bestErr == 0) return;
                    temp0 = max(1.0, (double)curErr);
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    int64 T;
    if (!(cin >> n >> T)) return 0;
    vector<int64> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&n);

    vector<uint8_t> bestBits(n, 0);
    int64 bestSum = 0;
    int64 bestErr = absDiff(0, T);

    // Initial greedy
    {
        vector<uint8_t> bits;
        int64 sum;
        greedyInit(a, T, bits, sum);
        int64 err = absDiff(sum, T);
        if (err < bestErr) {
            bestErr = err;
            bestSum = sum;
            bestBits = bits;
        }
    }

    // Multiple annealing runs
    int totalIters = 3000000;
    int runs = 6;
    for (int r = 0; r < runs && bestErr != 0; r++) {
        vector<uint8_t> bits;
        int64 sum;
        if (r == 0) {
            greedyInit(a, T, bits, sum);
        } else {
            randomInit(a, rng, bits, sum);
        }
        int iters = totalIters / runs;
        annealRun(a, T, bits, sum, iters, rng, bestBits, bestSum, bestErr);
    }

    // Local improvement
    if (bestErr != 0) {
        vector<uint8_t> bits = bestBits;
        int64 sum = bestSum;
        localImproveAllPairs(a, T, bits, sum);
        int64 err = absDiff(sum, T);
        if (err < bestErr) {
            bestErr = err;
            bestSum = sum;
            bestBits = bits;
        }
    }

    // MITM refinements on smallest and largest 40 values (or all if n<40)
    if (bestErr != 0 && n >= 1) {
        vector<int> ordAsc(n), ordDesc(n);
        iota(ordAsc.begin(), ordAsc.end(), 0);
        iota(ordDesc.begin(), ordDesc.end(), 0);
        sort(ordAsc.begin(), ordAsc.end(), [&](int i, int j) { return a[i] < a[j]; });
        sort(ordDesc.begin(), ordDesc.end(), [&](int i, int j) { return a[i] > a[j]; });

        int m = min(40, n);
        vector<int> selSmall(ordAsc.begin(), ordAsc.begin() + m);
        vector<int> selLarge(ordDesc.begin(), ordDesc.begin() + m);

        vector<uint8_t> candBits = bestBits;
        int64 candSum = bestSum;
        int64 candErr = bestErr;

        refineMITM(a, T, selSmall, bestBits, candBits, candSum, candErr);
        refineMITM(a, T, selLarge, candBits, candBits, candSum, candErr);

        // One more local improvement after MITM
        if (candErr < bestErr) {
            localImproveAllPairs(a, T, candBits, candSum);
            candErr = absDiff(candSum, T);
        }

        if (candErr < bestErr) {
            bestErr = candErr;
            bestSum = candSum;
            bestBits = candBits;
        }
    }

    // Output
    string out;
    out.reserve(n);
    for (int i = 0; i < n; i++) out.push_back(char('0' + (bestBits[i] ? 1 : 0)));
    cout << out << "\n";
    return 0;
}