#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 20;

struct SplitMix64 {
    uint64_t x;
    SplitMix64(uint64_t seed = 0) : x(seed) {}
    static uint64_t splitmix64(uint64_t &x) {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t nextU64() { return splitmix64(x); }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int bound) { return (int)(nextU64() % (uint64_t)bound); }
    double nextDouble() { return (nextU64() >> 11) * (1.0 / 9007199254740992.0); }
};

struct CustomHash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const noexcept {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

static inline int encChar(char c) { return c - 'A'; }
static inline char decChar(int v) { return char('A' + v); }

static inline uint64_t encodeKey(const vector<int> &s) {
    uint64_t code = 0;
    for (int v : s) code = (code << 3) | (uint64_t)v;
    uint64_t len = (uint64_t)s.size();
    return (len << 36) | code;
}

struct Solver {
    int N, M;
    vector<vector<int>> S;
    vector<int> L;
    unordered_map<uint64_t, vector<int>, CustomHash> keyToIds;

    int words;
    SplitMix64 rng;

    array<array<int, MAXN>, MAXN> mat{};
    array<array<int, MAXN>, MAXN> bestMat{};
    int bestC = -1;

    vector<vector<uint64_t>> lineBits;
    vector<int> cnt;
    int curC = 0;

    Solver(int N_, int M_) : N(N_), M(M_), rng(chrono::steady_clock::now().time_since_epoch().count()) {
        words = (M + 63) / 64;
    }

    inline int getRowVal(int r, int c) const { return mat[r][c]; }
    inline int getColVal(int r, int c) const { return mat[r][c]; }

    vector<uint64_t> computeLineBitsRow(int r) {
        vector<uint64_t> bits(words, 0);
        int vals[2 * MAXN];
        for (int p = 0; p < 2 * N; p++) vals[p] = mat[r][p % N];
        int maxLen = min(12, N);
        for (int st = 0; st < N; st++) {
            uint64_t code = 0;
            for (int len = 1; len <= maxLen; len++) {
                code = (code << 3) | (uint64_t)vals[st + len - 1];
                if (len >= 2) {
                    uint64_t key = ((uint64_t)len << 36) | code;
                    auto it = keyToIds.find(key);
                    if (it != keyToIds.end()) {
                        for (int id : it->second) bits[id >> 6] |= 1ULL << (id & 63);
                    }
                }
            }
        }
        return bits;
    }

    vector<uint64_t> computeLineBitsCol(int c) {
        vector<uint64_t> bits(words, 0);
        int vals[2 * MAXN];
        for (int p = 0; p < 2 * N; p++) vals[p] = mat[p % N][c];
        int maxLen = min(12, N);
        for (int st = 0; st < N; st++) {
            uint64_t code = 0;
            for (int len = 1; len <= maxLen; len++) {
                code = (code << 3) | (uint64_t)vals[st + len - 1];
                if (len >= 2) {
                    uint64_t key = ((uint64_t)len << 36) | code;
                    auto it = keyToIds.find(key);
                    if (it != keyToIds.end()) {
                        for (int id : it->second) bits[id >> 6] |= 1ULL << (id & 63);
                    }
                }
            }
        }
        return bits;
    }

    void rebuildAllLineBitsAndCounts() {
        lineBits.assign(2 * N, vector<uint64_t>(words, 0));
        cnt.assign(M, 0);
        curC = 0;

        for (int r = 0; r < N; r++) lineBits[r] = computeLineBitsRow(r);
        for (int c = 0; c < N; c++) lineBits[N + c] = computeLineBitsCol(c);

        for (int li = 0; li < 2 * N; li++) {
            for (int w = 0; w < words; w++) {
                uint64_t x = lineBits[li][w];
                while (x) {
                    int b = __builtin_ctzll(x);
                    int id = (w << 6) + b;
                    if (id < M) cnt[id] += 1;
                    x &= x - 1;
                }
            }
        }
        for (int i = 0; i < M; i++) if (cnt[i] > 0) curC++;
    }

    inline void applyLineUpdate(int li, const vector<uint64_t> &oldB, const vector<uint64_t> &newB) {
        (void)li;
        for (int w = 0; w < words; w++) {
            uint64_t oldW = oldB[w];
            uint64_t newW = newB[w];
            uint64_t removed = oldW & ~newW;
            uint64_t added = newW & ~oldW;

            while (removed) {
                int b = __builtin_ctzll(removed);
                int id = (w << 6) + b;
                if (id < M) {
                    int prev = cnt[id];
                    cnt[id] = prev - 1;
                    if (prev == 1) curC--;
                }
                removed &= removed - 1;
            }
            while (added) {
                int b = __builtin_ctzll(added);
                int id = (w << 6) + b;
                if (id < M) {
                    int prev = cnt[id];
                    cnt[id] = prev + 1;
                    if (prev == 0) curC++;
                }
                added &= added - 1;
            }
        }
    }

    int quickEvalMatchedCount() {
        vector<uint64_t> all(words, 0);
        for (int r = 0; r < N; r++) {
            auto bits = computeLineBitsRow(r);
            for (int w = 0; w < words; w++) all[w] |= bits[w];
        }
        for (int c = 0; c < N; c++) {
            auto bits = computeLineBitsCol(c);
            for (int w = 0; w < words; w++) all[w] |= bits[w];
        }
        int pc = 0;
        for (int w = 0; w < words; w++) pc += __builtin_popcountll(all[w]);
        return pc;
    }

    void greedyFillInit() {
        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) mat[i][j] = -1;

        int seed = 0;
        for (int i = 1; i < M; i++) if ((int)S[i].size() > (int)S[seed].size()) seed = i;

        // Place seed at (0,0) horizontally
        for (int p = 0; p < (int)S[seed].size(); p++) mat[0][p % N] = S[seed][p];

        // Place another long string vertically at (0,0) if compatible and shares start char
        int best2 = -1, seed2 = -1;
        for (int i = 0; i < M; i++) {
            if (i == seed) continue;
            if (S[i].empty()) continue;
            if (S[i][0] != mat[0][0]) continue;
            int matches = 0, conflicts = 0, overlap = 0;
            int ii = 0;
            for (int p = 0; p < (int)S[i].size(); p++) {
                int v = mat[ii][0];
                if (v != -1) {
                    overlap++;
                    if (v == S[i][p]) matches++;
                    else conflicts++;
                }
                ii++; if (ii == N) ii = 0;
            }
            if (conflicts == 0 && overlap > 0 && matches > best2) {
                best2 = matches;
                seed2 = i;
            }
        }
        if (seed2 != -1) {
            int ii = 0;
            for (int p = 0; p < (int)S[seed2].size(); p++) {
                if (mat[ii][0] == -1) mat[ii][0] = S[seed2][p];
                ii++; if (ii == N) ii = 0;
            }
        }

        vector<int> order(M);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            return S[a].size() > S[b].size();
        });

        int rounds = 10;
        for (int round = 0; round < rounds; round++) {
            bool changed = false;
            for (int id : order) {
                const auto &seq = S[id];
                int len = (int)seq.size();
                int minReq = (len >= 10 ? 3 : (len >= 7 ? 2 : 1));

                int bestMatch = -1;
                int bestI = -1, bestJ = -1, bestD = -1;

                for (int d = 0; d < 2; d++) {
                    for (int i = 0; i < N; i++) {
                        for (int j = 0; j < N; j++) {
                            int matches = 0, conflicts = 0, overlap = 0;
                            if (d == 0) {
                                int jj = j;
                                for (int p = 0; p < len; p++) {
                                    int v = mat[i][jj];
                                    if (v != -1) {
                                        overlap++;
                                        if (v == seq[p]) matches++;
                                        else conflicts++;
                                    }
                                    jj++; if (jj == N) jj = 0;
                                }
                            } else {
                                int ii = i;
                                for (int p = 0; p < len; p++) {
                                    int v = mat[ii][j];
                                    if (v != -1) {
                                        overlap++;
                                        if (v == seq[p]) matches++;
                                        else conflicts++;
                                    }
                                    ii++; if (ii == N) ii = 0;
                                }
                            }
                            if (overlap == 0) continue;
                            if (conflicts == 0 && matches > bestMatch) {
                                bestMatch = matches;
                                bestI = i; bestJ = j; bestD = d;
                            }
                        }
                    }
                }

                if (bestMatch >= minReq) {
                    if (bestD == 0) {
                        int jj = bestJ;
                        for (int p = 0; p < len; p++) {
                            if (mat[bestI][jj] == -1) {
                                mat[bestI][jj] = seq[p];
                                changed = true;
                            }
                            jj++; if (jj == N) jj = 0;
                        }
                    } else {
                        int ii = bestI;
                        for (int p = 0; p < len; p++) {
                            if (mat[ii][bestJ] == -1) {
                                mat[ii][bestJ] = seq[p];
                                changed = true;
                            }
                            ii++; if (ii == N) ii = 0;
                        }
                    }
                }
            }
            if (!changed) break;
        }

        // Fill unknowns
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if (mat[i][j] == -1) mat[i][j] = rng.nextInt(8);
            }
        }
    }

    void emRefine(int iters, chrono::steady_clock::time_point endTime) {
        vector<array<int, 8>> votes(N * N);
        for (int iter = 0; iter < iters; iter++) {
            if (chrono::steady_clock::now() >= endTime) break;
            for (auto &v : votes) v.fill(0);

            for (int id = 0; id < M; id++) {
                const auto &seq = S[id];
                int len = (int)seq.size();
                int bestScore = -1;
                int bestI = 0, bestJ = 0, bestD = 0;
                int ties = 0;

                for (int d = 0; d < 2; d++) {
                    for (int i = 0; i < N; i++) {
                        for (int j = 0; j < N; j++) {
                            int score = 0;
                            if (d == 0) {
                                int jj = j;
                                for (int p = 0; p < len; p++) {
                                    score += (mat[i][jj] == seq[p]);
                                    jj++; if (jj == N) jj = 0;
                                }
                            } else {
                                int ii = i;
                                for (int p = 0; p < len; p++) {
                                    score += (mat[ii][j] == seq[p]);
                                    ii++; if (ii == N) ii = 0;
                                }
                            }
                            if (score > bestScore) {
                                bestScore = score;
                                bestI = i; bestJ = j; bestD = d;
                                ties = 1;
                            } else if (score == bestScore) {
                                ties++;
                                if (rng.nextInt(ties) == 0) {
                                    bestI = i; bestJ = j; bestD = d;
                                }
                            }
                        }
                    }
                }

                int weight = 1 + bestScore;
                if (bestD == 0) {
                    int jj = bestJ;
                    for (int p = 0; p < len; p++) {
                        votes[bestI * N + jj][seq[p]] += weight;
                        jj++; if (jj == N) jj = 0;
                    }
                } else {
                    int ii = bestI;
                    for (int p = 0; p < len; p++) {
                        votes[ii * N + bestJ][seq[p]] += weight;
                        ii++; if (ii == N) ii = 0;
                    }
                }
            }

            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) {
                    auto &vv = votes[i * N + j];
                    int cur = mat[i][j];
                    int bestV = -1;
                    int bestL = cur;
                    int tie = 0;
                    for (int a = 0; a < 8; a++) {
                        int v = vv[a];
                        if (v > bestV) {
                            bestV = v; bestL = a; tie = 1;
                        } else if (v == bestV) {
                            tie++;
                            if (rng.nextInt(tie) == 0) bestL = a;
                        }
                    }
                    if (bestV > 0) mat[i][j] = bestL;
                }
            }

            int c = quickEvalMatchedCount();
            if (c > bestC) {
                bestC = c;
                for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) bestMat[i][j] = mat[i][j];
            }
        }

        if (bestC >= 0) {
            for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) mat[i][j] = bestMat[i][j];
        }
    }

    void saOptimize(chrono::steady_clock::time_point endTime) {
        rebuildAllLineBitsAndCounts();
        bestC = curC;
        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) bestMat[i][j] = mat[i][j];

        auto startTime = chrono::steady_clock::now();
        double T0 = 5.0, T1 = 0.2;

        int iter = 0;
        while (chrono::steady_clock::now() < endTime) {
            iter++;
            double t = chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
            double all = chrono::duration<double>(endTime - startTime).count();
            double prog = (all > 0 ? min(1.0, t / all) : 1.0);
            double temp = T0 * (1.0 - prog) + T1 * prog;

            int i = rng.nextInt(N);
            int j = rng.nextInt(N);
            int oldVal = mat[i][j];
            int newVal = rng.nextInt(7);
            if (newVal >= oldVal) newVal++;
            mat[i][j] = newVal;

            int rowLi = i;
            int colLi = N + j;

            vector<uint64_t> oldRow = lineBits[rowLi];
            vector<uint64_t> oldCol = lineBits[colLi];

            vector<uint64_t> newRow = computeLineBitsRow(i);
            vector<uint64_t> newCol = computeLineBitsCol(j);

            int prevC = curC;

            applyLineUpdate(rowLi, oldRow, newRow);
            applyLineUpdate(colLi, oldCol, newCol);

            int delta = curC - prevC;
            bool accept = false;
            if (delta >= 0) {
                accept = true;
            } else {
                double prob = exp((double)delta / temp);
                accept = (rng.nextDouble() < prob);
            }

            if (accept) {
                lineBits[rowLi] = std::move(newRow);
                lineBits[colLi] = std::move(newCol);
                if (curC > bestC) {
                    bestC = curC;
                    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) bestMat[r][c] = mat[r][c];
                }
            } else {
                // revert
                applyLineUpdate(rowLi, lineBits[rowLi], oldRow);
                applyLineUpdate(colLi, lineBits[colLi], oldCol);
                lineBits[rowLi] = std::move(oldRow);
                lineBits[colLi] = std::move(oldCol);
                curC = prevC;
                mat[i][j] = oldVal;
            }
        }

        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) mat[i][j] = bestMat[i][j];
    }

    void solve() {
        keyToIds.reserve((size_t)M * 2);

        greedyFillInit();

        auto start = chrono::steady_clock::now();
        auto endTime = start + chrono::milliseconds(1950);

        // quick evaluate current as initial best
        int c0 = quickEvalMatchedCount();
        bestC = c0;
        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) bestMat[i][j] = mat[i][j];

        emRefine(10, endTime);

        saOptimize(endTime);

        for (int i = 0; i < N; i++) {
            string out;
            out.reserve(N);
            for (int j = 0; j < N; j++) out.push_back(decChar(mat[i][j]));
            cout << out << "\n";
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    Solver solver(N, M);
    solver.S.resize(M);
    solver.L.resize(M);

    for (int i = 0; i < M; i++) {
        string s;
        cin >> s;
        solver.L[i] = (int)s.size();
        solver.S[i].resize(solver.L[i]);
        for (int j = 0; j < solver.L[i]; j++) solver.S[i][j] = encChar(s[j]);
        uint64_t key = encodeKey(solver.S[i]);
        solver.keyToIds[key].push_back(i);
    }

    solver.solve();
    return 0;
}