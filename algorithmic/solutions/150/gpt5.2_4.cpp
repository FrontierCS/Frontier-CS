#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct FastRng {
    uint64_t x;
    FastRng(uint64_t seed = 1) : x(seed) {}
    uint64_t nextU64() { return x = splitmix64(x); }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
    double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0); // 2^53
    }
};

struct U64Hash {
    size_t operator()(uint64_t x) const noexcept {
        x ^= x >> 23;
        x *= 0x2127599bf4325c37ULL;
        x ^= x >> 47;
        return (size_t)x;
    }
};

struct Timer {
    chrono::high_resolution_clock::time_point st;
    Timer() : st(chrono::high_resolution_clock::now()) {}
    double elapsedSec() const {
        auto ed = chrono::high_resolution_clock::now();
        return chrono::duration<double>(ed - st).count();
    }
};

static inline uint64_t packKey(int len, uint64_t code) {
    return (uint64_t(len) << 40) | code;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<string> s(M);
    int Lmax = 2;
    for (int i = 0; i < M; i++) {
        cin >> s[i];
        Lmax = max<int>(Lmax, (int)s[i].size());
    }
    Lmax = min(Lmax, 12);

    vector<vector<uint8_t>> ss(M);
    ss.reserve(M);
    for (int i = 0; i < M; i++) {
        ss[i].resize(s[i].size());
        for (int j = 0; j < (int)s[i].size(); j++) ss[i][j] = (uint8_t)(s[i][j] - 'A');
    }

    vector<int64_t> w(13, 0);
    for (int len = 2; len <= 12; len++) {
        int e = 2 * (len - 2);
        w[len] = (e >= 0 && e < 62) ? (1LL << e) : (1LL << 61);
    }

    unordered_map<uint64_t, int, U64Hash> need;
    unordered_map<uint64_t, int, U64Hash> full;
    need.reserve((size_t)M * 80);
    full.reserve((size_t)M * 2);

    for (int idx = 0; idx < M; idx++) {
        const auto &t = ss[idx];
        int n = (int)t.size();
        uint64_t codeFull = 0;
        for (int i = 0; i < n; i++) codeFull = (codeFull << 3) | t[i];
        full[packKey(n, codeFull)]++;

        for (int st = 0; st < n; st++) {
            uint64_t code = 0;
            for (int len = 1; st + len <= n && len <= Lmax; len++) {
                code = (code << 3) | t[st + len - 1];
                if (len >= 2) need[packKey(len, code)]++;
            }
        }
    }

    vector<string> byLen = s;
    sort(byLen.begin(), byLen.end(), [](const string& a, const string& b) {
        return a.size() > b.size();
    });

    FastRng rng(123456789);

    vector<vector<uint8_t>> g(N, vector<uint8_t>(N, 0));
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) g[i][j] = (uint8_t)rng.nextInt(8);

    auto pasteHorizontal = [&](int row, int start, const vector<uint8_t>& t) {
        for (int k = 0; k < (int)t.size(); k++) g[row][(start + k) % N] = t[k];
    };
    auto pasteVertical = [&](int col, int start, const vector<uint8_t>& t) {
        for (int k = 0; k < (int)t.size(); k++) g[(start + k) % N][col] = t[k];
    };

    for (int r = 0; r < N && r < (int)byLen.size(); r++) {
        int idx = r % M;
        int st = rng.nextInt(N);
        pasteHorizontal(r, st, ss[idx]);
    }
    for (int c = 0; c < N && c < (int)byLen.size(); c++) {
        int idx = (N + c) % M;
        int st = rng.nextInt(N);
        pasteVertical(c, st, ss[idx]);
    }

    unordered_map<uint64_t, int, U64Hash> occ;
    occ.reserve(20000);

    auto addOcc = [&](uint64_t key, int delta) {
        auto it = occ.find(key);
        int before = (it == occ.end()) ? 0 : it->second;
        int after = before + delta;
        if (after == 0) {
            if (it != occ.end()) occ.erase(it);
        } else {
            if (it == occ.end()) occ.emplace(key, after);
            else it->second = after;
        }
    };

    auto buildOccFromGrid = [&]() {
        occ.clear();
        for (int r = 0; r < N; r++) {
            for (int st = 0; st < N; st++) {
                uint64_t code = 0;
                for (int len = 1; len <= Lmax; len++) {
                    code = (code << 3) | g[r][(st + len - 1) % N];
                    if (len >= 2) addOcc(packKey(len, code), +1);
                }
            }
        }
        for (int c = 0; c < N; c++) {
            for (int st = 0; st < N; st++) {
                uint64_t code = 0;
                for (int len = 1; len <= Lmax; len++) {
                    code = (code << 3) | g[(st + len - 1) % N][c];
                    if (len >= 2) addOcc(packKey(len, code), +1);
                }
            }
        }
    };

    buildOccFromGrid();

    int64_t scoreSub = 0;
    int matchedFull = 0;

    auto recomputeScores = [&]() {
        scoreSub = 0;
        matchedFull = 0;

        for (const auto &kv : need) {
            uint64_t key = kv.first;
            int needCnt = kv.second;
            auto it = occ.find(key);
            int o = (it == occ.end()) ? 0 : it->second;
            int len = (int)(key >> 40);
            scoreSub += w[len] * (int64_t)min(o, needCnt);
        }
        for (const auto &kv : full) {
            uint64_t key = kv.first;
            int cnt = kv.second;
            if (occ.find(key) != occ.end()) matchedFull += cnt;
        }
    };

    recomputeScores();

    const int64_t FULLW = 5000000LL;

    auto objective = [&]() -> int64_t {
        return (int64_t)matchedFull * FULLW + scoreSub;
    };

    auto applyDeltaWithScore = [&](uint64_t key, int delta) {
        auto itOcc = occ.find(key);
        int before = (itOcc == occ.end()) ? 0 : itOcc->second;
        int after = before + delta;

        if (after == 0) {
            if (itOcc != occ.end()) occ.erase(itOcc);
        } else {
            if (itOcc == occ.end()) occ.emplace(key, after);
            else itOcc->second = after;
        }

        auto itNeed = need.find(key);
        if (itNeed != need.end()) {
            int needCnt = itNeed->second;
            int len = (int)(key >> 40);
            scoreSub += w[len] * (int64_t)(min(after, needCnt) - min(before, needCnt));
        }

        auto itFull = full.find(key);
        if (itFull != full.end()) {
            int fcnt = itFull->second;
            int b = (before > 0);
            int a = (after > 0);
            if (a != b) matchedFull += (a - b) * fcnt;
        }
    };

    auto applyDeltaOccOnly = [&](uint64_t key, int delta) {
        auto itOcc = occ.find(key);
        int before = (itOcc == occ.end()) ? 0 : itOcc->second;
        int after = before + delta;
        if (after == 0) {
            if (itOcc != occ.end()) occ.erase(itOcc);
        } else {
            if (itOcc == occ.end()) occ.emplace(key, after);
            else itOcc->second = after;
        }
    };

    vector<vector<uint8_t>> bestG = g;
    int bestFull = matchedFull;
    int64_t bestSub = scoreSub;

    auto updBest = [&]() {
        if (matchedFull > bestFull || (matchedFull == bestFull && scoreSub > bestSub)) {
            bestFull = matchedFull;
            bestSub = scoreSub;
            bestG = g;
        }
    };
    updBest();

    auto genSingleCellChanges = [&](int i, int j, uint8_t newVal, vector<pair<uint64_t,int>> &changes) {
        changes.clear();
        changes.reserve(4 * 90);

        uint8_t oldVal = g[i][j];
        if (oldVal == newVal) return;

        // Row i affected windows including position j
        for (int len = 2; len <= Lmax; len++) {
            for (int t = 0; t < len; t++) {
                int st = j - t;
                st %= N; if (st < 0) st += N;
                uint64_t oldCode = 0, newCode = 0;
                for (int k = 0; k < len; k++) {
                    int col = st + k;
                    col %= N;
                    uint8_t v = g[i][col];
                    oldCode = (oldCode << 3) | v;
                    newCode = (newCode << 3) | (col == j ? newVal : v);
                }
                changes.emplace_back(packKey(len, oldCode), -1);
                changes.emplace_back(packKey(len, newCode), +1);
            }
        }

        // Col j affected windows including position i
        for (int len = 2; len <= Lmax; len++) {
            for (int t = 0; t < len; t++) {
                int st = i - t;
                st %= N; if (st < 0) st += N;
                uint64_t oldCode = 0, newCode = 0;
                for (int k = 0; k < len; k++) {
                    int row = st + k;
                    row %= N;
                    uint8_t v = g[row][j];
                    oldCode = (oldCode << 3) | v;
                    newCode = (newCode << 3) | (row == i ? newVal : v);
                }
                changes.emplace_back(packKey(len, oldCode), -1);
                changes.emplace_back(packKey(len, newCode), +1);
            }
        }
    };

    auto buildKeysRow = [&](int r) {
        vector<uint64_t> keys;
        keys.reserve(N * (Lmax - 1));
        for (int st = 0; st < N; st++) {
            uint64_t code = 0;
            for (int len = 1; len <= Lmax; len++) {
                code = (code << 3) | g[r][(st + len - 1) % N];
                if (len >= 2) keys.push_back(packKey(len, code));
            }
        }
        return keys;
    };
    auto buildKeysCol = [&](int c) {
        vector<uint64_t> keys;
        keys.reserve(N * (Lmax - 1));
        for (int st = 0; st < N; st++) {
            uint64_t code = 0;
            for (int len = 1; len <= Lmax; len++) {
                code = (code << 3) | g[(st + len - 1) % N][c];
                if (len >= 2) keys.push_back(packKey(len, code));
            }
        }
        return keys;
    };

    Timer timer;
    const double TL = 1.85;
    const double T0 = 2.0e6;
    const double T1 = 2.0e4;

    vector<pair<uint64_t,int>> changes;
    vector<pair<uint64_t,int>> ops;
    vector<tuple<int,int,uint8_t>> modifiedCells;

    while (true) {
        double elapsed = timer.elapsedSec();
        if (elapsed >= TL) break;
        double prog = elapsed / TL;
        double temp = T0 * (1.0 - prog) + T1 * prog;

        int64_t oldObj = objective();
        int oldFull = matchedFull;
        int64_t oldSub = scoreSub;

        bool doPaste = (rng.nextDouble() < (0.03 * (1.0 - prog) + 0.01 * prog));

        if (!doPaste) {
            int i = rng.nextInt(N);
            int j = rng.nextInt(N);
            uint8_t oldVal = g[i][j];
            uint8_t newVal = (uint8_t)rng.nextInt(8);
            if (newVal == oldVal) continue;

            genSingleCellChanges(i, j, newVal, changes);
            for (auto &p : changes) applyDeltaWithScore(p.first, p.second);
            g[i][j] = newVal;

            int64_t newObj = objective();
            int64_t diff = newObj - oldObj;

            bool accept = false;
            if (diff >= 0) accept = true;
            else {
                double prob = exp((double)diff / temp);
                if (rng.nextDouble() < prob) accept = true;
            }

            if (!accept) {
                g[i][j] = oldVal;
                for (auto &p : changes) applyDeltaOccOnly(p.first, -p.second);
                matchedFull = oldFull;
                scoreSub = oldSub;
            } else {
                updBest();
            }
        } else {
            int idx = rng.nextInt(M);
            const auto &t = ss[idx];
            int len = (int)t.size();
            if (len < 2 || len > Lmax) continue;

            bool horiz = (rng.nextInt(2) == 0);
            int line = rng.nextInt(N);
            int st = rng.nextInt(N);

            modifiedCells.clear();
            modifiedCells.reserve(len);

            for (int k = 0; k < len; k++) {
                int r = horiz ? line : (st + k) % N;
                int c = horiz ? (st + k) % N : line;
                uint8_t oldv = g[r][c];
                uint8_t newv = t[k];
                if (oldv != newv) modifiedCells.emplace_back(r, c, oldv);
            }
            if (modifiedCells.empty()) continue;

            bool rowAff[20] = {0};
            bool colAff[20] = {0};
            vector<int> rows, cols;
            rows.reserve(13);
            cols.reserve(13);
            for (auto &mc : modifiedCells) {
                int r = get<0>(mc), c = get<1>(mc);
                if (!rowAff[r]) { rowAff[r] = true; rows.push_back(r); }
                if (!colAff[c]) { colAff[c] = true; cols.push_back(c); }
            }

            vector<vector<uint64_t>> oldRowKeys(rows.size()), oldColKeys(cols.size());
            for (int a = 0; a < (int)rows.size(); a++) oldRowKeys[a] = buildKeysRow(rows[a]);
            for (int a = 0; a < (int)cols.size(); a++) oldColKeys[a] = buildKeysCol(cols[a]);

            // apply cell modifications
            for (int k = 0; k < len; k++) {
                int r = horiz ? line : (st + k) % N;
                int c = horiz ? (st + k) % N : line;
                g[r][c] = t[k];
            }

            ops.clear();
            ops.reserve((rows.size() + cols.size()) * (size_t)N * (Lmax - 1) * 2);

            // apply deltas for affected rows
            for (int a = 0; a < (int)rows.size(); a++) {
                for (uint64_t key : oldRowKeys[a]) {
                    applyDeltaWithScore(key, -1);
                    ops.emplace_back(key, -1);
                }
                auto newKeys = buildKeysRow(rows[a]);
                for (uint64_t key : newKeys) {
                    applyDeltaWithScore(key, +1);
                    ops.emplace_back(key, +1);
                }
            }
            // affected cols
            for (int a = 0; a < (int)cols.size(); a++) {
                for (uint64_t key : oldColKeys[a]) {
                    applyDeltaWithScore(key, -1);
                    ops.emplace_back(key, -1);
                }
                auto newKeys = buildKeysCol(cols[a]);
                for (uint64_t key : newKeys) {
                    applyDeltaWithScore(key, +1);
                    ops.emplace_back(key, +1);
                }
            }

            int64_t newObj = objective();
            int64_t diff = newObj - oldObj;

            bool accept = false;
            if (diff >= 0) accept = true;
            else {
                double prob = exp((double)diff / temp);
                if (rng.nextDouble() < prob) accept = true;
            }

            if (!accept) {
                // revert grid
                for (auto &mc : modifiedCells) {
                    int r = get<0>(mc), c = get<1>(mc);
                    uint8_t oldv = get<2>(mc);
                    g[r][c] = oldv;
                }
                // revert occ only
                for (auto &p : ops) applyDeltaOccOnly(p.first, -p.second);
                matchedFull = oldFull;
                scoreSub = oldSub;
            } else {
                updBest();
            }
        }
    }

    static const char *ALPH = "ABCDEFGH";
    for (int i = 0; i < N; i++) {
        string out;
        out.resize(N);
        for (int j = 0; j < N; j++) out[j] = ALPH[bestG[i][j] & 7];
        cout << out << "\n";
    }
    return 0;
}