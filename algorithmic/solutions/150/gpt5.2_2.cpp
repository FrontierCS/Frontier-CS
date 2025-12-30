#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
struct CustomHash {
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM =
            (uint64_t)chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

struct RNG {
    uint64_t x;
    explicit RNG(uint64_t seed) : x(seed) {}
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
    inline double nextDouble() {
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

static constexpr int MAXLEN = 12;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<string> reads(M);
    int maxReadLen = 0;
    for (int i = 0; i < M; i++) {
        cin >> reads[i];
        maxReadLen = max(maxReadLen, (int)reads[i].size());
    }

    vector<__int128> pow8(MAXLEN + 1);
    pow8[0] = 1;
    for (int i = 1; i <= MAXLEN; i++) pow8[i] = pow8[i - 1] * 8;

    auto encodeStringKey = [&](const string& s) -> uint64_t {
        uint64_t code = 0;
        for (char ch : s) code = code * 8 + (uint64_t)(ch - 'A');
        return ((uint64_t)s.size() << 36) | code;
    };

    unordered_map<uint64_t, int, CustomHash> id;
    id.reserve(2048);
    vector<int> weight;
    weight.reserve(M);

    for (int i = 0; i < M; i++) {
        uint64_t key = encodeStringKey(reads[i]);
        auto it = id.find(key);
        if (it == id.end()) {
            int nid = (int)weight.size();
            id.emplace(key, nid);
            weight.push_back(1);
        } else {
            weight[it->second]++;
        }
    }
    int K = (int)weight.size();

    auto buildRowPref = [&](const vector<string>& g, int r, int overrideC = -1, int overrideDigit = -1) {
        array<__int128, 41> pref{};
        pref[0] = 0;
        for (int t = 0; t < 2 * N; t++) {
            int c = t % N;
            int d = (c == overrideC ? overrideDigit : (int)(g[r][c] - 'A'));
            pref[t + 1] = pref[t] * 8 + d;
        }
        return pref;
    };
    auto buildColPref = [&](const vector<string>& g, int c, int overrideR = -1, int overrideDigit = -1) {
        array<__int128, 41> pref{};
        pref[0] = 0;
        for (int t = 0; t < 2 * N; t++) {
            int r = t % N;
            int d = (r == overrideR ? overrideDigit : (int)(g[r][c] - 'A'));
            pref[t + 1] = pref[t] * 8 + d;
        }
        return pref;
    };

    auto getCode = [&](const array<__int128, 41>& pref, int start, int len) -> uint64_t {
        __int128 v = pref[start + len] - pref[start] * pow8[len];
        return (uint64_t)v;
    };

    auto computeScore = [&](const vector<string>& g) -> int {
        vector<unsigned char> present(K, 0);
        int score = 0;

        for (int r = 0; r < N; r++) {
            auto pref = buildRowPref(g, r);
            for (int st = 0; st < N; st++) {
                for (int len = 2; len <= MAXLEN; len++) {
                    uint64_t code = getCode(pref, st, len);
                    uint64_t key = ((uint64_t)len << 36) | code;
                    auto it = id.find(key);
                    if (it != id.end()) present[it->second] = 1;
                }
            }
        }
        for (int c = 0; c < N; c++) {
            auto pref = buildColPref(g, c);
            for (int st = 0; st < N; st++) {
                for (int len = 2; len <= MAXLEN; len++) {
                    uint64_t code = getCode(pref, st, len);
                    uint64_t key = ((uint64_t)len << 36) | code;
                    auto it = id.find(key);
                    if (it != id.end()) present[it->second] = 1;
                }
            }
        }

        for (int i = 0; i < K; i++) if (present[i]) score += weight[i];
        return score;
    };

    RNG rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count() ^ 0x123456789abcdefULL);

    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        return reads[a].size() > reads[b].size();
    });

    auto greedyBuild = [&](int variant) -> vector<string> {
        vector<string> g(N, string(N, '.'));

        // Shuffle within equal length groups for diversity
        vector<int> ord = order;
        for (int i = 0; i < M; ) {
            int j = i;
            int L = (int)reads[ord[i]].size();
            while (j < M && (int)reads[ord[j]].size() == L) j++;
            for (int k = j - 1; k > i; k--) {
                int p = i + rng.nextInt(k - i + 1);
                swap(ord[k], ord[p]);
            }
            i = j;
        }

        auto apply = [&](const string& s, int dir, int si, int sj) -> int {
            int gain = 0;
            int len = (int)s.size();
            for (int p = 0; p < len; p++) {
                int r = (si + (dir == 1 ? p : 0)) % N;
                int c = (sj + (dir == 0 ? p : 0)) % N;
                if (g[r][c] == '.') {
                    g[r][c] = s[p];
                    gain++;
                }
            }
            return gain;
        };

        auto bestPlace = [&](const string& s, int& outDir, int& outI, int& outJ, int& outGain, int& outOverlap) -> bool {
            int bestOverlap = -1, bestGain = -1;
            int bestDir = 0, bestI = 0, bestJ = 0;
            int len = (int)s.size();

            for (int dir = 0; dir < 2; dir++) {
                for (int i = 0; i < N; i++) {
                    for (int j = 0; j < N; j++) {
                        int overlap = 0, gain = 0;
                        bool ok = true;
                        for (int p = 0; p < len; p++) {
                            int r = (i + (dir == 1 ? p : 0)) % N;
                            int c = (j + (dir == 0 ? p : 0)) % N;
                            char cur = g[r][c];
                            if (cur == '.') gain++;
                            else if (cur == s[p]) overlap++;
                            else { ok = false; break; }
                        }
                        if (!ok) continue;

                        if (overlap > bestOverlap || (overlap == bestOverlap && gain > bestGain)) {
                            bestOverlap = overlap;
                            bestGain = gain;
                            bestDir = dir;
                            bestI = i;
                            bestJ = j;
                        }
                    }
                }
            }

            if (bestOverlap < 0) return false;
            outDir = bestDir;
            outI = bestI;
            outJ = bestJ;
            outGain = bestGain;
            outOverlap = bestOverlap;
            return true;
        };

        int assigned = 0;
        // anchor
        int anchorIdx = ord[0];
        int dir0 = variant & 1;
        int si0 = (variant * 7 + 3) % N;
        int sj0 = (variant * 11 + 5) % N;
        assigned += apply(reads[anchorIdx], dir0, si0, sj0);

        for (int pass = 0; pass < 2; pass++) {
            for (int t = 0; t < M; t++) {
                int idx = ord[t];
                if (pass == 0 && idx == anchorIdx) continue;

                int dir, si, sj, gain, overlap;
                if (!bestPlace(reads[idx], dir, si, sj, gain, overlap)) continue;

                bool accept = (overlap >= 1) || (assigned < 120);
                if (!accept) continue;
                assigned += apply(reads[idx], dir, si, sj);
            }
        }

        // Fill remaining with random letters
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if (g[i][j] == '.') g[i][j] = char('A' + rng.nextInt(8));
            }
        }
        return g;
    };

    auto randomBuild = [&]() -> vector<string> {
        vector<string> g(N, string(N, 'A'));
        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) g[i][j] = char('A' + rng.nextInt(8));
        return g;
    };

    vector<string> bestInit = randomBuild();
    int bestInitScore = computeScore(bestInit);

    int restarts = 8;
    for (int r = 0; r < restarts; r++) {
        vector<string> g = greedyBuild(r);
        int sc = computeScore(g);
        if (sc > bestInitScore) {
            bestInitScore = sc;
            bestInit = std::move(g);
        }
    }
    for (int r = 0; r < 2; r++) {
        vector<string> g = randomBuild();
        int sc = computeScore(g);
        if (sc > bestInitScore) {
            bestInitScore = sc;
            bestInit = std::move(g);
        }
    }

    // State for SA
    vector<string> g = bestInit;
    vector<array<__int128, 41>> rowPref(N), colPref(N);
    for (int r = 0; r < N; r++) rowPref[r] = buildRowPref(g, r);
    for (int c = 0; c < N; c++) colPref[c] = buildColPref(g, c);

    vector<int> counts(K, 0);
    int score = 0;

    auto incKey = [&](int idx) {
        if (counts[idx] == 0) score += weight[idx];
        counts[idx]++;
    };
    auto buildCounts = [&]() {
        fill(counts.begin(), counts.end(), 0);
        score = 0;
        for (int r = 0; r < N; r++) {
            auto& pref = rowPref[r];
            for (int st = 0; st < N; st++) {
                for (int len = 2; len <= MAXLEN; len++) {
                    uint64_t code = getCode(pref, st, len);
                    uint64_t key = ((uint64_t)len << 36) | code;
                    auto it = id.find(key);
                    if (it != id.end()) incKey(it->second);
                }
            }
        }
        for (int c = 0; c < N; c++) {
            auto& pref = colPref[c];
            for (int st = 0; st < N; st++) {
                for (int len = 2; len <= MAXLEN; len++) {
                    uint64_t code = getCode(pref, st, len);
                    uint64_t key = ((uint64_t)len << 36) | code;
                    auto it = id.find(key);
                    if (it != id.end()) incKey(it->second);
                }
            }
        }
    };

    buildCounts();

    vector<int> deltaCnt(K, 0);
    vector<unsigned char> used(K, 0);
    vector<int> touched;
    touched.reserve(256);

    auto resetTemp = [&]() {
        for (int idx : touched) {
            deltaCnt[idx] = 0;
            used[idx] = 0;
        }
        touched.clear();
    };

    auto accumulateAffected = [&](const array<__int128, 41>& pref, int pos, int sign) {
        for (int len = 2; len <= MAXLEN; len++) {
            for (int off = 0; off < len; off++) {
                int st = pos - off;
                if (st < 0) st += N;
                uint64_t code = getCode(pref, st, len);
                uint64_t key = ((uint64_t)len << 36) | code;
                auto it = id.find(key);
                if (it == id.end()) continue;
                int idx = it->second;
                if (!used[idx]) {
                    used[idx] = 1;
                    touched.push_back(idx);
                }
                deltaCnt[idx] += sign;
            }
        }
    };

    auto computeMove = [&](int r, int c, int newDigit, array<__int128, 41>& newRow, array<__int128, 41>& newCol) -> int {
        touched.clear();
        // old
        accumulateAffected(rowPref[r], c, -1);
        accumulateAffected(colPref[c], r, -1);
        // new prefs
        newRow = buildRowPref(g, r, c, newDigit);
        newCol = buildColPref(g, c, r, newDigit);
        // new
        accumulateAffected(newRow, c, +1);
        accumulateAffected(newCol, r, +1);

        int deltaScore = 0;
        for (int idx : touched) {
            int d = deltaCnt[idx];
            if (d == 0) continue;
            int before = counts[idx];
            int after = before + d;
            if (before == 0 && after > 0) deltaScore += weight[idx];
            else if (before > 0 && after == 0) deltaScore -= weight[idx];
        }
        return deltaScore;
    };

    auto applyMove = [&](int r, int c, int newDigit, const array<__int128, 41>& newRow, const array<__int128, 41>& newCol, int deltaScore) {
        g[r][c] = char('A' + newDigit);
        rowPref[r] = newRow;
        colPref[c] = newCol;

        for (int idx : touched) {
            int d = deltaCnt[idx];
            if (d != 0) counts[idx] += d;
        }
        score += deltaScore;
    };

    // Coordinate ascent (one pass)
    {
        for (int r = 0; r < N; r++) {
            for (int c = 0; c < N; c++) {
                int cur = g[r][c] - 'A';
                int bestD = cur;
                int bestDelta = 0;

                for (int d = 0; d < 8; d++) {
                    if (d == cur) continue;
                    array<__int128, 41> nr, nc;
                    int deltaScore = computeMove(r, c, d, nr, nc);
                    if (deltaScore > bestDelta) {
                        bestDelta = deltaScore;
                        bestD = d;
                    }
                    resetTemp();
                }

                if (bestD != cur) {
                    array<__int128, 41> nr, nc;
                    int deltaScore = computeMove(r, c, bestD, nr, nc);
                    if (deltaScore > 0) applyMove(r, c, bestD, nr, nc, deltaScore);
                    resetTemp();
                }
            }
        }
    }

    vector<string> bestGrid = g;
    int bestScore = score;

    auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.95;

    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
    };

    int iters = 0;
    while (true) {
        double t = elapsedSec();
        if (t >= TIME_LIMIT) break;
        double frac = t / TIME_LIMIT;
        double temp = 30.0 * (1.0 - frac) + 0.5 * frac;

        int r = rng.nextInt(N);
        int c = rng.nextInt(N);
        int cur = g[r][c] - 'A';
        int nd = rng.nextInt(8);
        if (nd == cur) continue;

        array<__int128, 41> nr, nc;
        int deltaScore = computeMove(r, c, nd, nr, nc);

        bool accept = false;
        if (deltaScore >= 0) {
            accept = true;
        } else {
            double prob = exp((double)deltaScore / temp);
            if (rng.nextDouble() < prob) accept = true;
        }

        if (accept) {
            applyMove(r, c, nd, nr, nc, deltaScore);
            if (score > bestScore) {
                bestScore = score;
                bestGrid = g;
            }
        }
        resetTemp();
        iters++;
    }

    for (int i = 0; i < N; i++) {
        cout << bestGrid[i] << "\n";
    }
    return 0;
}