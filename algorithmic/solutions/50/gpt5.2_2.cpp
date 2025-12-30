#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline int popcnt64(uint64_t x) {
    return (int)__builtin_popcountll(x);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<long long> cost(m);
    for (int i = 0; i < m; i++) fs.readInt(cost[i]);

    static constexpr int MAXW = 7; // ceil(400/64)=7
    int W = (n + 63) / 64;

    vector<array<uint64_t, MAXW>> setMask(m);
    for (int s = 0; s < m; s++) setMask[s].fill(0);

    vector<vector<int>> elemsOfSet(m);
    vector<vector<int>> setsOfElem(n);

    for (int e = 0; e < n; e++) {
        int k;
        fs.readInt(k);
        setsOfElem[e].reserve(k);
        for (int j = 0; j < k; j++) {
            int id;
            fs.readInt(id);
            --id;
            if (id < 0 || id >= m) continue;
            setsOfElem[e].push_back(id);
            elemsOfSet[id].push_back(e);
            setMask[id][e >> 6] |= 1ULL << (e & 63);
        }
    }

    auto isEmptyMask = [&](const array<uint64_t, MAXW> &mask) -> bool {
        for (int w = 0; w < W; w++) if (mask[w]) return false;
        return true;
    };

    auto popcntInter = [&](const array<uint64_t, MAXW> &a, const array<uint64_t, MAXW> &b) -> int {
        int res = 0;
        for (int w = 0; w < W; w++) res += popcnt64(a[w] & b[w]);
        return res;
    };

    auto applyRemove = [&](array<uint64_t, MAXW> &a, const array<uint64_t, MAXW> &b) {
        for (int w = 0; w < W; w++) a[w] &= ~b[w];
    };

    auto greedySolve = [&](uint64_t seed, double eps, bool randomized) -> pair<long long, vector<int>> {
        mt19937_64 rng(seed);
        vector<uint8_t> chosen(m, 0);
        vector<int> picked;
        picked.reserve(m);

        array<uint64_t, MAXW> uncovered;
        uncovered.fill(0);
        for (int w = 0; w < W; w++) uncovered[w] = ~0ULL;
        if (n % 64) uncovered[W - 1] = (1ULL << (n % 64)) - 1;
        for (int w = W; w < MAXW; w++) uncovered[w] = 0;

        while (!isEmptyMask(uncovered)) {
            int best = -1;
            int bestGain = 0;
            double bestRatio = -1.0;

            // First pass: best ratio
            for (int s = 0; s < m; s++) if (!chosen[s]) {
                int gain = popcntInter(setMask[s], uncovered);
                if (gain <= 0) continue;
                double ratio;
                if (cost[s] == 0) ratio = 1e200;
                else ratio = (double)gain / (double)cost[s];
                if (ratio > bestRatio + 1e-18 || (abs(ratio - bestRatio) <= 1e-18 && gain > bestGain)) {
                    bestRatio = ratio;
                    best = s;
                    bestGain = gain;
                }
            }
            if (best == -1) break;

            int chosenSet = best;
            if (randomized && eps > 0.0) {
                double thr = bestRatio * (1.0 - eps);
                vector<int> rcl;
                rcl.reserve(64);
                for (int s = 0; s < m; s++) if (!chosen[s]) {
                    int gain = popcntInter(setMask[s], uncovered);
                    if (gain <= 0) continue;
                    double ratio;
                    if (cost[s] == 0) ratio = 1e200;
                    else ratio = (double)gain / (double)cost[s];
                    if (ratio + 1e-18 >= thr) rcl.push_back(s);
                }
                if (!rcl.empty()) {
                    uniform_int_distribution<int> dist(0, (int)rcl.size() - 1);
                    chosenSet = rcl[dist(rng)];
                }
            }

            chosen[chosenSet] = 1;
            picked.push_back(chosenSet);
            applyRemove(uncovered, setMask[chosenSet]);
        }

        // Fallback for uncovered elements: pick cheapest set for each uncovered element.
        if (!isEmptyMask(uncovered)) {
            for (int e = 0; e < n; e++) {
                if (((uncovered[e >> 6] >> (e & 63)) & 1ULL) == 0ULL) continue;
                long long bestC = LLONG_MAX;
                int bestS = -1;
                for (int s : setsOfElem[e]) {
                    if (cost[s] < bestC) {
                        bestC = cost[s];
                        bestS = s;
                    }
                }
                if (bestS == -1) continue; // impossible element
                if (!chosen[bestS]) {
                    chosen[bestS] = 1;
                    picked.push_back(bestS);
                }
                // mark element as covered (and potentially others)
                applyRemove(uncovered, setMask[bestS]);
            }
        }

        // If still uncovered and no sets exist for some element, return empty (infeasible).
        if (!isEmptyMask(uncovered)) {
            return {LLONG_MAX / 4, vector<int>()};
        }

        // Prune redundant sets (remove expensive first), repeat to fix cascading redundancies.
        vector<int> coverCount(n, 0);
        for (int s : picked) {
            for (int e : elemsOfSet[s]) coverCount[e]++;
        }

        bool changed = true;
        while (changed) {
            changed = false;
            vector<int> order;
            order.reserve(picked.size());
            for (int s : picked) if (chosen[s]) order.push_back(s);
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (cost[a] != cost[b]) return cost[a] > cost[b];
                return a < b;
            });

            for (int s : order) {
                if (!chosen[s]) continue;
                bool removable = true;
                for (int e : elemsOfSet[s]) {
                    if (coverCount[e] <= 1) { removable = false; break; }
                }
                if (!removable) continue;
                chosen[s] = 0;
                for (int e : elemsOfSet[s]) coverCount[e]--;
                changed = true;
            }
        }

        // Ensure coverage after pruning; add cheapest sets for any uncovered elements.
        vector<int> finalPicked;
        finalPicked.reserve(picked.size());
        for (int s = 0; s < m; s++) if (chosen[s]) finalPicked.push_back(s);

        vector<int> cnt(n, 0);
        for (int s : finalPicked) for (int e : elemsOfSet[s]) cnt[e]++;

        for (int e = 0; e < n; e++) if (cnt[e] == 0) {
            long long bestC = LLONG_MAX;
            int bestS = -1;
            for (int s : setsOfElem[e]) {
                if (cost[s] < bestC) { bestC = cost[s]; bestS = s; }
            }
            if (bestS == -1) continue; // impossible element
            if (!chosen[bestS]) {
                chosen[bestS] = 1;
                finalPicked.push_back(bestS);
                for (int x : elemsOfSet[bestS]) cnt[x]++;
            }
        }

        // Compute total cost
        long long total = 0;
        for (int s : finalPicked) total += cost[s];
        sort(finalPicked.begin(), finalPicked.end());
        finalPicked.erase(unique(finalPicked.begin(), finalPicked.end()), finalPicked.end());
        return {total, finalPicked};
    };

    auto t0 = chrono::steady_clock::now();

    pair<long long, vector<int>> best = {LLONG_MAX, vector<int>()};

    // Deterministic greedy
    {
        auto res = greedySolve(1234567ULL, 0.0, false);
        if (res.first < best.first) best = std::move(res);
    }

    // Randomized runs
    vector<double> epsList = {0.03, 0.07, 0.12, 0.20};
    uint64_t baseSeed = 987654321ULL ^ (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    for (int it = 0; it < 12; it++) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        if (elapsed > 8.8) break;

        double eps = epsList[it % (int)epsList.size()];
        auto res = greedySolve(baseSeed + 1000003ULL * (uint64_t)it, eps, true);
        if (res.first < best.first) best = std::move(res);
    }

    if (best.second.empty()) {
        // As a last resort, try cover each element by cheapest set.
        vector<uint8_t> chosen(m, 0);
        vector<int> picked;
        for (int e = 0; e < n; e++) {
            long long bestC = LLONG_MAX;
            int bestS = -1;
            for (int s : setsOfElem[e]) {
                if (cost[s] < bestC) { bestC = cost[s]; bestS = s; }
            }
            if (bestS == -1) continue;
            if (!chosen[bestS]) { chosen[bestS] = 1; picked.push_back(bestS); }
        }
        best.second = picked;
    }

    cout << best.second.size() << "\n";
    for (size_t i = 0; i < best.second.size(); i++) {
        if (i) cout << ' ';
        cout << (best.second[i] + 1);
    }
    cout << "\n";
    return 0;
}