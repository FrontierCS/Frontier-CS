#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

struct Solver {
    int n, m, W;
    vector<long long> cost;
    vector<uint64_t> B; // flattened m x W bitsets
    uint64_t lastMask;
    chrono::steady_clock::time_point timeEnd;

    Solver(int n_, int m_) : n(n_), m(m_) {
        W = (n + 63) / 64;
        B.assign((size_t)m * W, 0);
        if (n % 64 == 0) lastMask = ~0ULL;
        else lastMask = (1ULL << (n % 64)) - 1ULL;
    }

    inline uint64_t* setBits(int j) { return &B[(size_t)j * W]; }
    inline const uint64_t* setBits(int j) const { return &B[(size_t)j * W]; }

    inline int popcount_and(const uint64_t* a, const uint64_t* b) const {
        int s = 0;
        for (int k = 0; k < W; ++k) s += __builtin_popcountll(a[k] & b[k]);
        return s;
    }
    inline int popcount_vec(const uint64_t* a) const {
        int s = 0;
        for (int k = 0; k < W; ++k) s += __builtin_popcountll(a[k]);
        return s;
    }

    struct Solution {
        vector<unsigned char> selected; // 0/1
        vector<int> coverCount; // size n
        long long totalCost;
        Solution() : totalCost(0) {}
    };

    void updateCoverCountAdd(Solution &sol, int j) const {
        const uint64_t* sj = setBits(j);
        for (int w = 0; w < W; ++w) {
            uint64_t x = sj[w];
            while (x) {
                int t = __builtin_ctzll(x);
                int idx = w * 64 + t;
                if (idx < n) {
                    sol.coverCount[idx]++;
                }
                x &= x - 1;
            }
        }
    }
    void updateCoverCountRemove(Solution &sol, int j) const {
        const uint64_t* sj = setBits(j);
        for (int w = 0; w < W; ++w) {
            uint64_t x = sj[w];
            while (x) {
                int t = __builtin_ctzll(x);
                int idx = w * 64 + t;
                if (idx < n) {
                    sol.coverCount[idx]--;
                }
                x &= x - 1;
            }
        }
    }

    Solution greedy_build(const vector<double> &randFactor) const {
        Solution sol;
        sol.selected.assign(m, 0);
        sol.coverCount.assign(n, 0);
        sol.totalCost = 0;

        vector<uint64_t> U(W, ~0ULL);
        U[W - 1] &= lastMask;

        int uncovered = n;
        // Pre-check union of all sets to ensure coverable
        vector<uint64_t> unionAll(W, 0);
        for (int j = 0; j < m; ++j) {
            const uint64_t* sj = setBits(j);
            for (int w = 0; w < W; ++w) unionAll[w] |= sj[w];
        }
        bool ok = true;
        for (int w = 0; w < W; ++w) {
            uint64_t need = (w == W - 1) ? lastMask : ~0ULL;
            if ((unionAll[w] & need) != need) { ok = false; break; }
        }
        if (!ok) {
            // Fallback: select all sets that cover something to output something, though problem likely guarantees coverable
            for (int j = 0; j < m; ++j) {
                sol.selected[j] = 1;
                sol.totalCost += cost[j];
                updateCoverCountAdd(sol, j);
            }
            return sol;
        }

        vector<char> used(m, 0);
        while (uncovered > 0) {
            int bestJ = -1;
            double bestScore = numeric_limits<double>::infinity();
            int bestGain = 0;

            for (int j = 0; j < m; ++j) if (!sol.selected[j]) {
                const uint64_t* sj = setBits(j);
                int gain = 0;
                for (int w = 0; w < W; ++w) gain += __builtin_popcountll(U[w] & sj[w]);
                if (gain <= 0) continue;
                double rf = randFactor.empty() ? 1.0 : randFactor[j];
                double score = (double)cost[j] * rf / (double)gain;
                if (score < bestScore || (score == bestScore && (gain > bestGain || (gain == bestGain && cost[j] < (bestJ >= 0 ? cost[bestJ] : LLONG_MAX))))) {
                    bestScore = score;
                    bestJ = j;
                    bestGain = gain;
                }
            }
            if (bestJ == -1) {
                // Should not happen if coverable
                break;
            }
            sol.selected[bestJ] = 1;
            sol.totalCost += cost[bestJ];

            // Update U and coverCount
            const uint64_t* sj = setBits(bestJ);
            for (int w = 0; w < W; ++w) {
                U[w] &= ~sj[w];
            }
            for (int w = 0; w < W; ++w) {
                uint64_t x = sj[w];
                while (x) {
                    int t = __builtin_ctzll(x);
                    int idx = w * 64 + t;
                    if (idx < n) {
                        if (sol.coverCount[idx] == 0) uncovered--;
                        sol.coverCount[idx]++;
                    }
                    x &= x - 1;
                }
            }
        }

        return sol;
    }

    void prune_redundant(Solution &sol) const {
        bool changed = true;
        // To avoid many scans, do a few passes
        int passes = 0;
        while (changed && passes < 3) {
            changed = false;
            ++passes;
            for (int j = 0; j < m; ++j) if (sol.selected[j]) {
                bool redundant = true;
                const uint64_t* sj = setBits(j);
                for (int w = 0; w < W && redundant; ++w) {
                    uint64_t x = sj[w];
                    while (x) {
                        int t = __builtin_ctzll(x);
                        int idx = w * 64 + t;
                        if (idx < n) {
                            if (sol.coverCount[idx] <= 1) { redundant = false; break; }
                        }
                        x &= x - 1;
                    }
                }
                if (redundant) {
                    sol.selected[j] = 0;
                    sol.totalCost -= cost[j];
                    updateCoverCountRemove(sol, j);
                    changed = true;
                }
            }
        }
    }

    bool swap_1_to_1(Solution &sol) const {
        bool improved = false;
        vector<int> selList;
        selList.reserve(m);
        for (int j = 0; j < m; ++j) if (sol.selected[j]) selList.push_back(j);
        // Sort by decreasing cost to try expensive sets first
        sort(selList.begin(), selList.end(), [&](int a, int b){ return cost[a] > cost[b]; });

        vector<uint64_t> crit(W);
        for (int idx = 0; idx < (int)selList.size(); ++idx) {
            if (chrono::steady_clock::now() > timeEnd) break;
            int s = selList[idx];
            if (!sol.selected[s]) continue;
            // Build critical bitset
            fill(crit.begin(), crit.end(), 0ULL);
            const uint64_t* ss = setBits(s);
            for (int w = 0; w < W; ++w) {
                uint64_t x = ss[w];
                while (x) {
                    int t = __builtin_ctzll(x);
                    int e = w * 64 + t;
                    if (e < n && sol.coverCount[e] == 1) {
                        crit[w] |= (1ULL << t);
                    }
                    x &= x - 1;
                }
            }
            bool hasCrit = false;
            for (int w = 0; w < W; ++w) if (crit[w]) { hasCrit = true; break; }
            if (!hasCrit) {
                // Redundant, remove
                sol.selected[s] = 0;
                sol.totalCost -= cost[s];
                updateCoverCountRemove(sol, s);
                improved = true;
                continue;
            }
            int bestT = -1;
            long long bestCost = LLONG_MAX;
            for (int t = 0; t < m; ++t) {
                if (sol.selected[t]) continue;
                if (cost[t] >= cost[s]) continue;
                const uint64_t* tt = setBits(t);
                bool covers = true;
                for (int w = 0; w < W; ++w) {
                    if ( (crit[w] & ~tt[w]) != 0ULL ) { covers = false; break; }
                }
                if (!covers) continue;
                if (cost[t] < bestCost) {
                    bestCost = cost[t];
                    bestT = t;
                }
            }
            if (bestT != -1) {
                // perform swap
                sol.selected[s] = 0;
                updateCoverCountRemove(sol, s);
                sol.selected[bestT] = 1;
                updateCoverCountAdd(sol, bestT);
                sol.totalCost += cost[bestT] - cost[s];
                improved = true;
            }
        }
        return improved;
    }

    bool swap_1_to_2(Solution &sol, int Kcap = 60) const {
        bool improved = false;
        vector<int> selList;
        selList.reserve(m);
        for (int j = 0; j < m; ++j) if (sol.selected[j]) selList.push_back(j);
        // Try expensive sets first
        sort(selList.begin(), selList.end(), [&](int a, int b){ return cost[a] > cost[b]; });

        vector<uint64_t> crit(W);
        vector<int> candIds;
        vector<double> candScore;
        vector<long long> candCost;
        vector<uint64_t> masks; // flattened: len = Kcap * W

        for (int idx = 0; idx < (int)selList.size(); ++idx) {
            if (chrono::steady_clock::now() > timeEnd) break;
            int s = selList[idx];
            if (!sol.selected[s]) continue;
            // Build critical bitset B_s
            fill(crit.begin(), crit.end(), 0ULL);
            const uint64_t* ss = setBits(s);
            int critCount = 0;
            for (int w = 0; w < W; ++w) {
                uint64_t x = ss[w];
                while (x) {
                    int t = __builtin_ctzll(x);
                    int e = w * 64 + t;
                    if (e < n && sol.coverCount[e] == 1) {
                        crit[w] |= (1ULL << t);
                        ++critCount;
                    }
                    x &= x - 1;
                }
            }
            bool hasCrit = false;
            for (int w = 0; w < W; ++w) if (crit[w]) { hasCrit = true; break; }
            if (!hasCrit) {
                // redundant
                sol.selected[s] = 0;
                sol.totalCost -= cost[s];
                updateCoverCountRemove(sol, s);
                improved = true;
                continue;
            }

            // Candidate sets that cover at least one critical element
            candIds.clear();
            candScore.clear();
            candCost.clear();
            // Preliminary arrays for all candidates to select top Kcap by ratio
            // We'll gather (ratio, id) pairs
            vector<pair<double,int>> heap;
            heap.reserve(min(m, 1024));
            for (int t = 0; t < m; ++t) {
                if (sol.selected[t]) continue;
                if (cost[t] >= cost[s]) continue;
                const uint64_t* tt = setBits(t);
                int g = 0;
                for (int w = 0; w < W; ++w) g += __builtin_popcountll(crit[w] & tt[w]);
                if (g <= 0) continue;
                double ratio = (double)cost[t] / (double)g;
                heap.emplace_back(ratio, t);
            }
            if (heap.empty()) continue;
            if ((int)heap.size() > Kcap) {
                nth_element(heap.begin(), heap.begin() + Kcap, heap.end(),
                            [](const pair<double,int> &a, const pair<double,int> &b){ return a.first < b.first; });
                heap.resize(Kcap);
            }
            sort(heap.begin(), heap.end(),
                 [](const pair<double,int> &a, const pair<double,int> &b){ return a.first < b.first; });

            int K = (int)heap.size();
            candIds.reserve(K);
            candScore.reserve(K);
            candCost.reserve(K);
            masks.assign((size_t)K * W, 0ULL);

            for (int ci = 0; ci < K; ++ci) {
                int t = heap[ci].second;
                candIds.push_back(t);
                candScore.push_back(heap[ci].first);
                candCost.push_back(cost[t]);
                const uint64_t* tt = setBits(t);
                for (int w = 0; w < W; ++w) {
                    masks[(size_t)ci * W + w] = crit[w] & tt[w];
                }
            }

            // Find best pair
            long long bestSum = LLONG_MAX;
            int bestI = -1, bestJ = -1;
            for (int i = 0; i < K; ++i) {
                if (candCost[i] >= cost[s]) continue; // since j has positive cost, sum will be >= cost[s]
                for (int j = i + 1; j < K; ++j) {
                    long long sumc = candCost[i] + candCost[j];
                    if (sumc >= cost[s]) continue;
                    bool covers = true;
                    for (int w = 0; w < W; ++w) {
                        uint64_t u = masks[(size_t)i * W + w] | masks[(size_t)j * W + w];
                        if (u != crit[w]) { covers = false; break; }
                    }
                    if (!covers) continue;
                    if (sumc < bestSum) {
                        bestSum = sumc; bestI = i; bestJ = j;
                    }
                }
            }
            if (bestI != -1) {
                int t1 = candIds[bestI];
                int t2 = candIds[bestJ];
                // apply replacement
                sol.selected[s] = 0;
                updateCoverCountRemove(sol, s);
                sol.selected[t1] = 1;
                updateCoverCountAdd(sol, t1);
                sol.selected[t2] = 1;
                updateCoverCountAdd(sol, t2);
                sol.totalCost += bestSum - cost[s];
                improved = true;
                // optional prune to remove redundancy introduced by added sets
                prune_redundant(sol);
            }
        }
        return improved;
    }

    vector<int> selected_to_ids(const Solution &sol) const {
        vector<int> ids;
        ids.reserve(m);
        for (int j = 0; j < m; ++j) if (sol.selected[j]) ids.push_back(j + 1);
        return ids;
    }

    bool valid_cover(const Solution &sol) const {
        for (int i = 0; i < n; ++i) if (sol.coverCount[i] <= 0) return false;
        return true;
    }

    void run() {
        // Time budget: 10s limit; use 9.5 seconds
        timeEnd = chrono::steady_clock::now() + chrono::milliseconds(9500);

        // Initial run without randomness
        vector<double> noRF;
        Solution best = greedy_build(noRF);
        prune_redundant(best);
        while (swap_1_to_1(best)) {
            if (chrono::steady_clock::now() > timeEnd) break;
            prune_redundant(best);
        }
        if (chrono::steady_clock::now() < timeEnd) {
            swap_1_to_2(best);
            prune_redundant(best);
        }
        if (!valid_cover(best)) {
            // fallback: select all sets
            best.selected.assign(m, 0);
            best.coverCount.assign(n, 0);
            best.totalCost = 0;
            for (int j = 0; j < m; ++j) {
                best.selected[j] = 1;
                best.totalCost += cost[j];
                updateCoverCountAdd(best, j);
            }
        }

        long long bestCost = best.totalCost;
        vector<unsigned char> bestSel = best.selected;

        // Multi-start greedy with randomization
        std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
        uniform_real_distribution<double> dist(0.8, 1.2);
        int iter = 0;
        while (chrono::steady_clock::now() < timeEnd) {
            ++iter;
            vector<double> rf(m);
            for (int j = 0; j < m; ++j) rf[j] = dist(rng);
            Solution sol = greedy_build(rf);
            prune_redundant(sol);

            while (swap_1_to_1(sol)) {
                if (chrono::steady_clock::now() > timeEnd) break;
                prune_redundant(sol);
            }
            if (chrono::steady_clock::now() < timeEnd) {
                swap_1_to_2(sol);
                prune_redundant(sol);
            }

            if (valid_cover(sol) && sol.totalCost < bestCost) {
                bestCost = sol.totalCost;
                bestSel = sol.selected;
            }
        }

        // Prepare output
        vector<int> ans;
        ans.reserve(m);
        for (int j = 0; j < m; ++j) if (bestSel[j]) ans.push_back(j + 1);

        printf("%zu\n", ans.size());
        if (!ans.empty()) {
            for (size_t i = 0; i < ans.size(); ++i) {
                if (i) putchar(' ');
                printf("%d", ans[i]);
            }
        }
        putchar('\n');
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.nextInt(n)) return 0;
    fs.nextInt(m);

    Solver solver(n, m);
    solver.cost.resize(m);
    for (int i = 0; i < m; ++i) {
        long long c;
        fs.nextInt(c);
        solver.cost[i] = c;
    }

    for (int i = 0; i < n; ++i) {
        int k;
        fs.nextInt(k);
        for (int j = 0; j < k; ++j) {
            int a;
            fs.nextInt(a);
            --a;
            if (a >= 0 && a < m) {
                solver.setBits(a)[i / 64] |= (1ULL << (i % 64));
            }
        }
    }

    solver.run();
    return 0;
}