#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct RNG {
    uint64_t x;
    RNG() {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        x = splitmix64(seed);
    }
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU64() % (uint64_t)(hi - lo + 1));
    }
    inline double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<string> s(M);
    for (int i = 0; i < M; i++) cin >> s[i];

    // Constraints say N=20 always, but support N<=20.
    const int MAXN = 20;
    const int MAX2N = 40;

    vector<uint64_t> pow8(13, 1);
    for (int i = 1; i <= 12; i++) pow8[i] = pow8[i - 1] * 8ULL;

    vector<long long> wLen(13, 0);
    wLen[2] = 1;
    for (int l = 3; l <= 12; l++) wLen[l] = wLen[l - 1] * 4LL; // 4^(l-2)

    // Build weighted keys: all substrings (length 2..len) of input strings.
    vector<unordered_map<uint64_t, int>> mpLen(13);
    for (int l = 2; l <= 12; l++) {
        mpLen[l].reserve(4096);
        mpLen[l].max_load_factor(0.7f);
    }

    vector<long long> weight;
    weight.reserve(70000);

    auto encodeBits = [&](const string& t) -> uint64_t {
        uint64_t bits = 0;
        for (char c : t) bits = bits * 8ULL + (uint64_t)(c - 'A');
        return bits;
    };

    for (const string& str : s) {
        int L = (int)str.size();
        for (int i = 0; i < L; i++) {
            uint64_t bits = 0;
            for (int j = i; j < L; j++) {
                bits = bits * 8ULL + (uint64_t)(str[j] - 'A');
                int len = j - i + 1;
                if (len < 2 || len > 12) continue;
                auto &mp = mpLen[len];
                auto it = mp.find(bits);
                int idx;
                if (it == mp.end()) {
                    idx = (int)weight.size();
                    mp.emplace(bits, idx);
                    weight.push_back(0);
                } else {
                    idx = it->second;
                }
                weight[idx] += wLen[len];
            }
        }
    }

    vector<int> usedLens;
    usedLens.reserve(11);
    for (int l = 2; l <= 12; l++) if (!mpLen[l].empty()) usedLens.push_back(l);

    int U = (int)weight.size();
    vector<int> occ(U, 0);
    vector<int> delta(U, 0);
    vector<int> touched;
    touched.reserve(1024);

    auto addDelta = [&](int idx, int d) {
        if (delta[idx] == 0) touched.push_back(idx);
        delta[idx] += d;
    };

    RNG rng;

    array<array<uint8_t, MAXN>, MAXN> g{};
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) g[i][j] = (uint8_t)rng.nextInt(0, 7);

    array<array<uint8_t, MAX2N>, MAXN> rowVal{};
    array<array<uint8_t, MAX2N>, MAXN> colVal{};
    array<array<uint64_t, MAX2N + 1>, MAXN> rowPref{};
    array<array<uint64_t, MAX2N + 1>, MAXN> colPref{};

    auto rebuildRow = [&](int r) {
        rowPref[r][0] = 0;
        for (int t = 0; t < 2 * N; t++) rowPref[r][t + 1] = rowPref[r][t] * 8ULL + (uint64_t)rowVal[r][t];
    };
    auto rebuildCol = [&](int c) {
        colPref[c][0] = 0;
        for (int t = 0; t < 2 * N; t++) colPref[c][t + 1] = colPref[c][t] * 8ULL + (uint64_t)colVal[c][t];
    };
    auto getBitsRow = [&](int r, int start, int len) -> uint64_t {
        // modulo 2^64 arithmetic; exact for len<=12
        return rowPref[r][start + len] - rowPref[r][start] * pow8[len];
    };
    auto getBitsCol = [&](int c, int start, int len) -> uint64_t {
        return colPref[c][start + len] - colPref[c][start] * pow8[len];
    };

    for (int i = 0; i < N; i++) {
        for (int t = 0; t < N; t++) {
            rowVal[i][t] = g[i][t];
            rowVal[i][t + N] = g[i][t];
        }
        rebuildRow(i);
    }
    for (int j = 0; j < N; j++) {
        for (int t = 0; t < N; t++) {
            colVal[j][t] = g[t][j];
            colVal[j][t + N] = g[t][j];
        }
        rebuildCol(j);
    }

    long long score = 0;
    auto initCounts = [&]() {
        fill(occ.begin(), occ.end(), 0);
        score = 0;
        for (int r = 0; r < N; r++) {
            for (int st = 0; st < N; st++) {
                for (int len : usedLens) {
                    uint64_t bits = getBitsRow(r, st, len);
                    auto it = mpLen[len].find(bits);
                    if (it != mpLen[len].end()) {
                        int idx = it->second;
                        occ[idx]++;
                        score += weight[idx];
                    }
                }
            }
        }
        for (int c = 0; c < N; c++) {
            for (int st = 0; st < N; st++) {
                for (int len : usedLens) {
                    uint64_t bits = getBitsCol(c, st, len);
                    auto it = mpLen[len].find(bits);
                    if (it != mpLen[len].end()) {
                        int idx = it->second;
                        occ[idx]++;
                        score += weight[idx];
                    }
                }
            }
        }
    };
    initCounts();

    auto calcDeltaScore = [&](int i, int j, uint8_t newVal) -> long long {
        touched.clear();
        long long dScore = 0;

        uint8_t oldVal = g[i][j];
        if (oldVal == newVal) return 0;

        int diff = (int)newVal - (int)oldVal;

        // Affected substrings in row i (position j)
        for (int len : usedLens) {
            const uint64_t* p8 = pow8.data();
            for (int off = 0; off < len; off++) {
                int start = j - off;
                if (start < 0) start += N;
                uint64_t bitsOld = getBitsRow(i, start, len);
                long long bitsNewLL = (long long)bitsOld + (long long)diff * (long long)p8[len - 1 - off];
                uint64_t bitsNew = (uint64_t)bitsNewLL;
                if (bitsOld == bitsNew) continue;

                auto &mp = mpLen[len];
                auto itOld = mp.find(bitsOld);
                if (itOld != mp.end()) {
                    int idx = itOld->second;
                    addDelta(idx, -1);
                    dScore -= weight[idx];
                }
                auto itNew = mp.find(bitsNew);
                if (itNew != mp.end()) {
                    int idx = itNew->second;
                    addDelta(idx, +1);
                    dScore += weight[idx];
                }
            }
        }

        // Affected substrings in col j (position i)
        for (int len : usedLens) {
            const uint64_t* p8 = pow8.data();
            for (int off = 0; off < len; off++) {
                int start = i - off;
                if (start < 0) start += N;
                uint64_t bitsOld = getBitsCol(j, start, len);
                long long bitsNewLL = (long long)bitsOld + (long long)diff * (long long)p8[len - 1 - off];
                uint64_t bitsNew = (uint64_t)bitsNewLL;
                if (bitsOld == bitsNew) continue;

                auto &mp = mpLen[len];
                auto itOld = mp.find(bitsOld);
                if (itOld != mp.end()) {
                    int idx = itOld->second;
                    addDelta(idx, -1);
                    dScore -= weight[idx];
                }
                auto itNew = mp.find(bitsNew);
                if (itNew != mp.end()) {
                    int idx = itNew->second;
                    addDelta(idx, +1);
                    dScore += weight[idx];
                }
            }
        }

        return dScore;
    };

    auto resetDeltaTouched = [&]() {
        for (int idx : touched) delta[idx] = 0;
        touched.clear();
    };

    auto applyAccepted = [&]() {
        for (int idx : touched) {
            occ[idx] += delta[idx];
            // if (occ[idx] < 0) occ[idx] = 0; // should not happen
            delta[idx] = 0;
        }
        touched.clear();
    };

    auto applyCell = [&](int i, int j, uint8_t newVal) {
        g[i][j] = newVal;

        rowVal[i][j] = newVal;
        rowVal[i][j + N] = newVal;
        rebuildRow(i);

        colVal[j][i] = newVal;
        colVal[j][i + N] = newVal;
        rebuildCol(j);
    };

    // Calibrate temperature
    double avgAbs = 0.0;
    int calib = 200;
    for (int t = 0; t < calib; t++) {
        int i = rng.nextInt(0, N - 1);
        int j = rng.nextInt(0, N - 1);
        uint8_t oldVal = g[i][j];
        uint8_t newVal = (uint8_t)rng.nextInt(0, 7);
        if (newVal == oldVal) newVal = (uint8_t)((newVal + 1 + rng.nextInt(0, 6)) & 7);
        long long d = calcDeltaScore(i, j, newVal);
        avgAbs += (double)llabs(d);
        resetDeltaTouched();
    }
    avgAbs /= max(1, calib);
    if (avgAbs < 1.0) avgAbs = 1.0;

    double T0 = avgAbs * 2.0;
    double T1 = max(1.0, avgAbs * 0.02);

    array<array<uint8_t, MAXN>, MAXN> bestg = g;
    long long bestScore = score;

    auto tStart = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85;

    uint64_t iters = 0;
    while (true) {
        iters++;
        if ((iters & 1023) == 0) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - tStart).count();
            if (elapsed > TIME_LIMIT) break;
        }

        int i = rng.nextInt(0, N - 1);
        int j = rng.nextInt(0, N - 1);
        uint8_t oldVal = g[i][j];
        uint8_t newVal = (uint8_t)rng.nextInt(0, 7);
        if (newVal == oldVal) newVal = (uint8_t)((newVal + 1 + rng.nextInt(0, 6)) & 7);

        long long dScore = calcDeltaScore(i, j, newVal);

        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - tStart).count();
        double r = min(1.0, elapsed / TIME_LIMIT);
        double T = T0 * pow(T1 / T0, r);

        bool accept = false;
        if (dScore >= 0) {
            accept = true;
        } else {
            double p = exp((double)dScore / T);
            if (rng.nextDouble() < p) accept = true;
        }

        if (accept) {
            score += dScore;
            applyAccepted();
            applyCell(i, j, newVal);

            if (score > bestScore) {
                bestScore = score;
                bestg = g;
            }
        } else {
            resetDeltaTouched();
        }
    }

    for (int i = 0; i < N; i++) {
        string line;
        line.reserve(N);
        for (int j = 0; j < N; j++) line.push_back((char)('A' + bestg[i][j]));
        cout << line << "\n";
    }
    return 0;
}