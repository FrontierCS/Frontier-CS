#include <bits/stdc++.h>
using namespace std;

struct SetData {
    vector<uint64_t> bits;
    vector<int> elems;
    long long cost = 0;
    int id = 0; // 0-based
};

static inline int popcnt64(uint64_t x) {
    return __builtin_popcountll(x);
}

int n, m;
int W; // number of 64-bit words
vector<uint64_t> validMask; // mask for each word, last masked to n bits
vector<SetData> sets;
vector<vector<int>> elemToSets;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

static inline int gainForSet(int j, const vector<uint64_t>& C) {
    int gain = 0;
    const auto& sb = sets[j].bits;
    for (int w = 0; w < W; ++w) {
        uint64_t newbits = sb[w] & (~C[w] & validMask[w]);
        gain += popcnt64(newbits);
    }
    return gain;
}

static inline void orBits(vector<uint64_t>& C, const vector<uint64_t>& A) {
    for (int w = 0; w < W; ++w) C[w] |= A[w];
}

static inline bool coversAll(const vector<uint64_t>& sup, const vector<uint64_t>& sub) {
    // sup is the set; check superset: sub subset of sup, i.e., (sub & ~sup) == 0
    for (int w = 0; w < W; ++w) {
        if ((sub[w] & ~sup[w]) != 0ULL) return false;
    }
    return true;
}

static inline bool coversAllMask(const vector<uint64_t>& sup, const vector<uint64_t>& needMask) {
    for (int w = 0; w < W; ++w) {
        if ((needMask[w] & ~sup[w]) != 0ULL) return false;
    }
    return true;
}

static inline long long totalCost(const vector<int>& sel) {
    long long c = 0;
    for (int s : sel) c += sets[s].cost;
    return c;
}

vector<int> greedyRun(double noiseScale, const chrono::steady_clock::time_point& deadline) {
    vector<double> wcost(m);
    uniform_real_distribution<double> ur(-1.0, 1.0);
    for (int j = 0; j < m; ++j) {
        double noise = (noiseScale > 0 ? noiseScale * ur(rng) : 0.0);
        double wc = (double)sets[j].cost * (1.0 + noise);
        if (wc < 1e-9) wc = 1e-9;
        wcost[j] = wc;
    }

    vector<uint64_t> C(W, 0ULL);
    int covered = 0;
    vector<int> selected;
    vector<char> used(m, 0);

    // Pre-check: build a list of elements covered by any set
    vector<int> elemCovered(n, 0);
    for (int j = 0; j < m; ++j) for (int e : sets[j].elems) elemCovered[e] = 1;

    // Greedy selection
    while (covered < n) {
        if (chrono::steady_clock::now() > deadline) break;
        int best = -1;
        double bestScore = -1.0;
        int bestGain = 0;
        long long bestCost = LLONG_MAX;

        for (int j = 0; j < m; ++j) if (!used[j]) {
            int g = gainForSet(j, C);
            if (g <= 0) continue;
            double score = (double)g / wcost[j];
            if (score > bestScore - 1e-18) {
                bool better = false;
                if (score > bestScore + 1e-18) better = true;
                else {
                    // tie-breaker: lower cost, then higher gain, then lower id
                    if (sets[j].cost < bestCost) better = true;
                    else if (sets[j].cost == bestCost) {
                        if (g > bestGain) better = true;
                        else if (g == bestGain && j < best) better = true;
                    }
                }
                if (better) {
                    best = j;
                    bestScore = score;
                    bestGain = g;
                    bestCost = sets[j].cost;
                }
            }
        }
        if (best == -1) break;
        used[best] = 1;
        selected.push_back(best);
        // update covered
        for (int w = 0; w < W; ++w) {
            uint64_t newbits = sets[best].bits[w] & (~C[w] & validMask[w]);
            covered += popcnt64(newbits);
            C[w] |= sets[best].bits[w];
        }
    }

    if (covered < n) {
        // Fallback: cover remaining elements individually by choosing cheapest set that contains it
        vector<char> coveredElem(n, 0);
        for (int w = 0; w < W; ++w) {
            uint64_t x = C[w];
            int base = w * 64;
            while (x) {
                int b = __builtin_ctzll(x);
                int idx = base + b;
                if (idx < n) coveredElem[idx] = 1;
                x &= x - 1;
            }
        }
        vector<char> selectedFlag(m, 0);
        for (int s : selected) selectedFlag[s] = 1;

        for (int i = 0; i < n; ++i) if (!coveredElem[i]) {
            long long bestC = LLONG_MAX;
            int bestSet = -1;
            for (int s : elemToSets[i]) {
                if (sets[s].cost < bestC) {
                    bestC = sets[s].cost;
                    bestSet = s;
                }
            }
            if (bestSet != -1 && !selectedFlag[bestSet]) {
                selectedFlag[bestSet] = 1;
                selected.push_back(bestSet);
                for (int w = 0; w < W; ++w) {
                    uint64_t newbits = sets[bestSet].bits[w] & (~C[w] & validMask[w]);
                    covered += popcnt64(newbits);
                    C[w] |= sets[bestSet].bits[w];
                }
            }
        }
    }

    return selected;
}

vector<int> pruneExpensiveFirst(const vector<int>& initialSel) {
    vector<char> selectedFlag(m, 0);
    for (int s : initialSel) selectedFlag[s] = 1;

    vector<int> cnt(n, 0);
    for (int s : initialSel) {
        for (int e : sets[s].elems) cnt[e]++;
    }

    vector<int> order = initialSel;
    sort(order.begin(), order.end(), [&](int a, int b){
        if (sets[a].cost != sets[b].cost) return sets[a].cost > sets[b].cost;
        return a < b;
    });

    for (int s : order) {
        bool removable = true;
        for (int e : sets[s].elems) {
            if (cnt[e] <= 1) { removable = false; break; }
        }
        if (removable) {
            for (int e : sets[s].elems) cnt[e]--;
            selectedFlag[s] = 0;
        }
    }

    vector<int> res;
    res.reserve(initialSel.size());
    for (int s : initialSel) if (selectedFlag[s]) res.push_back(s);
    return res;
}

void buildCountsAndFlags(const vector<int>& sel, vector<int>& cnt, vector<char>& selectedFlag) {
    fill(cnt.begin(), cnt.end(), 0);
    fill(selectedFlag.begin(), selectedFlag.end(), 0);
    for (int s : sel) {
        selectedFlag[s] = 1;
        for (int e : sets[s].elems) cnt[e]++;
    }
}

bool oneToOneReplacement(vector<int>& sel, const chrono::steady_clock::time_point& deadline) {
    vector<char> selectedFlag(m, 0);
    for (int s : sel) selectedFlag[s] = 1;

    vector<int> cnt(n, 0);
    for (int s : sel) for (int e : sets[s].elems) cnt[e]++;

    bool improved = false;
    // Order by decreasing cost
    vector<int> order = sel;
    sort(order.begin(), order.end(), [&](int a, int b){
        if (sets[a].cost != sets[b].cost) return sets[a].cost > sets[b].cost;
        return a < b;
    });

    vector<uint64_t> needMask(W, 0ULL);

    for (int s : order) {
        if (chrono::steady_clock::now() > deadline) break;

        // Build needMask = elements exclusively covered by s
        bool hasNeed = false;
        for (int w = 0; w < W; ++w) needMask[w] = 0ULL;
        for (int e : sets[s].elems) {
            if (cnt[e] == 1) {
                hasNeed = true;
                int w = e >> 6;
                int b = e & 63;
                needMask[w] |= (1ULL << b);
            }
        }
        if (!hasNeed) continue;

        long long bestC = sets[s].cost - 1; // need strictly cheaper
        int bestT = -1;
        for (int t = 0; t < m; ++t) if (!selectedFlag[t]) {
            if (sets[t].cost >= sets[s].cost) continue;
            if (coversAllMask(sets[t].bits, needMask)) {
                if (sets[t].cost < bestC) {
                    bestC = sets[t].cost;
                    bestT = t;
                }
            }
        }
        if (bestT != -1) {
            // swap s -> bestT
            selectedFlag[s] = 0;
            selectedFlag[bestT] = 1;
            // update counts
            for (int e : sets[s].elems) cnt[e]--;
            for (int e : sets[bestT].elems) cnt[e]++;
            // update sel list: replace s with bestT
            for (int i = 0; i < (int)sel.size(); ++i) if (sel[i] == s) { sel[i] = bestT; break; }
            improved = true;
        }
    }

    if (improved) {
        // After swaps, prune again
        sel = pruneExpensiveFirst(sel);
    }
    return improved;
}

bool addThenPruneAttempt(vector<int>& sel, const chrono::steady_clock::time_point& deadline) {
    if (chrono::steady_clock::now() > deadline) return false;

    vector<char> selectedFlag(m, 0);
    for (int s : sel) selectedFlag[s] = 1;

    vector<int> cnt(n, 0);
    for (int s : sel) for (int e : sets[s].elems) cnt[e]++;

    // Build element weights
    vector<double> ew(n, 0.0);
    for (int i = 0; i < n; ++i) {
        if (cnt[i] > 0) ew[i] = 1.0 / (double)cnt[i];
        else ew[i] = 10.0; // uncovered shouldn't happen, but give high weight
    }

    // Sample candidates
    int samples = min(50, m);
    uniform_int_distribution<int> dis(0, m - 1);
    double bestScore = -1.0;
    int bestT = -1;
    for (int k = 0; k < samples; ++k) {
        if (chrono::steady_clock::now() > deadline) break;
        int t = dis(rng);
        if (selectedFlag[t]) continue;
        if (sets[t].elems.empty()) continue;
        double score = 0.0;
        for (int e : sets[t].elems) score += ew[e];
        score /= (double)max(1LL, sets[t].cost);
        if (score > bestScore) {
            bestScore = score;
            bestT = t;
        }
    }
    if (bestT == -1) return false;

    // Snapshot
    vector<int> cntOld = cnt;
    vector<int> selOld = sel;
    vector<char> selectedFlagOld = selectedFlag;
    long long costOld = totalCost(sel);

    // Add bestT
    selectedFlag[bestT] = 1;
    sel.push_back(bestT);
    for (int e : sets[bestT].elems) cnt[e]++;

    // Prune expensive-first
    vector<int> order = sel;
    sort(order.begin(), order.end(), [&](int a, int b){
        if (sets[a].cost != sets[b].cost) return sets[a].cost > sets[b].cost;
        return a < b;
    });
    for (int s : order) {
        if (!selectedFlag[s]) continue;
        bool removable = true;
        for (int e : sets[s].elems) {
            if (cnt[e] <= 1) { removable = false; break; }
        }
        if (removable) {
            selectedFlag[s] = 0;
            for (int e : sets[s].elems) cnt[e]--;
        }
    }
    vector<int> newSel;
    newSel.reserve(sel.size());
    for (int s : sel) if (selectedFlag[s]) newSel.push_back(s);
    long long costNew = totalCost(newSel);

    if (costNew < costOld) {
        sel.swap(newSel);
        return true;
    } else {
        // rollback
        sel.swap(selOld);
        return false;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> m)) {
        return 0;
    }

    sets.resize(m);
    for (int j = 0; j < m; ++j) {
        long long c; cin >> c;
        sets[j].cost = c;
        sets[j].id = j;
    }

    W = (n + 63) >> 6;
    validMask.assign(W, ~0ULL);
    if (W > 0) {
        int rem = n & 63;
        if (rem != 0) validMask[W - 1] = (rem == 64 ? ~0ULL : ((1ULL << rem) - 1ULL));
        else validMask[W - 1] = ~0ULL;
    }

    for (int j = 0; j < m; ++j) {
        sets[j].bits.assign(W, 0ULL);
    }

    elemToSets.assign(n, {});
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        for (int t = 0; t < k; ++t) {
            int a; cin >> a;
            int s = a - 1;
            if (s < 0 || s >= m) continue;
            sets[s].elems.push_back(i);
            int w = i >> 6;
            int b = i & 63;
            sets[s].bits[w] |= (1ULL << b);
            elemToSets[i].push_back(s);
        }
    }

    auto t0 = chrono::steady_clock::now();
    auto deadline = t0 + chrono::milliseconds(9700);

    // Greedy multi-start
    vector<int> bestSel;
    long long bestCost = LLONG_MAX;
    int runs = 0;

    auto greedyDeadline = t0 + (deadline - t0) / 2; // use about half time for initializing

    // Ensure at least one deterministic greedy run
    {
        vector<int> sel = greedyRun(0.0, deadline);
        sel = pruneExpensiveFirst(sel);
        long long c = totalCost(sel);
        if (c < bestCost) {
            bestCost = c;
            bestSel = sel;
        }
        runs++;
    }

    while (chrono::steady_clock::now() < greedyDeadline && runs < 200) {
        double noiseScale = 0.25;
        vector<int> sel = greedyRun(noiseScale, greedyDeadline);
        sel = pruneExpensiveFirst(sel);
        long long c = totalCost(sel);
        if (c < bestCost) {
            bestCost = c;
            bestSel = sel;
        }
        runs++;
    }

    // Improvements on best
    vector<int> sel = bestSel;

    // One-to-one replacement loop
    while (chrono::steady_clock::now() < deadline) {
        bool improved = oneToOneReplacement(sel, deadline);
        if (!improved) break;
    }

    // Random add-then-prune attempts
    int attempts = 0;
    while (chrono::steady_clock::now() < deadline && attempts < 200) {
        bool imp = addThenPruneAttempt(sel, deadline);
        attempts++;
        if (!imp && attempts % 20 == 0) {
            // also try one-to-one occasionally
            oneToOneReplacement(sel, deadline);
        }
    }

    // Final prune just in case
    sel = pruneExpensiveFirst(sel);

    cout << sel.size() << "\n";
    for (size_t i = 0; i < sel.size(); ++i) {
        if (i) cout << ' ';
        cout << (sets[sel[i]].id + 1);
    }
    cout << "\n";
    return 0;
}