#include <bits/stdc++.h>
using namespace std;

struct HeapNode {
    double key;
    int id;
    double benefitAtInsert;
    bool operator<(const HeapNode &other) const {
        return key > other.key; // for min-heap behavior
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        cout << 0 << "\n\n";
        return 0;
    }
    vector<long long> cost(m);
    for (int i = 0; i < m; ++i) cin >> cost[i];

    vector<vector<int>> setsOfElem(n);
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        vector<int> v;
        v.reserve(k);
        for (int j = 0; j < k; ++j) {
            int a; cin >> a; --a;
            if (a >= 0 && a < m) v.push_back(a);
        }
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
        setsOfElem[i] = move(v);
    }

    vector<vector<int>> elemsOfSet(m);
    for (int e = 0; e < n; ++e) {
        for (int s : setsOfElem[e]) {
            elemsOfSet[s].push_back(e);
        }
    }

    // Check if some element cannot be covered
    for (int e = 0; e < n; ++e) {
        if (setsOfElem[e].empty()) {
            cout << 0 << "\n\n";
            return 0;
        }
    }

    // Bitset representation for sets
    int W = (n + 63) >> 6;
    vector<vector<uint64_t>> setBits(m, vector<uint64_t>(W, 0));
    for (int s = 0; s < m; ++s) {
        for (int e : elemsOfSet[s]) {
            setBits[s][e >> 6] |= (1ULL << (e & 63));
        }
    }

    auto compute_cost = [&](const vector<char> &sel) -> long long {
        long long total = 0;
        for (int i = 0; i < m; ++i) if (sel[i]) total += cost[i];
        return total;
    };

    auto is_valid_cover = [&](const vector<char> &sel) -> bool {
        vector<int> cover(n, 0);
        for (int s = 0; s < m; ++s) if (sel[s]) {
            for (int e : elemsOfSet[s]) cover[e]++;
        }
        for (int e = 0; e < n; ++e) if (cover[e] == 0) return false;
        return true;
    };

    auto prune = [&](vector<char> &sel) {
        bool changed = true;
        vector<int> cover(n, 0);
        for (int s = 0; s < m; ++s) if (sel[s]) {
            for (int e : elemsOfSet[s]) cover[e]++;
        }
        vector<int> order;
        order.reserve(m);
        for (int s = 0; s < m; ++s) if (sel[s]) order.push_back(s);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (cost[a] != cost[b]) return cost[a] > cost[b];
            return elemsOfSet[a].size() > elemsOfSet[b].size();
        });
        while (changed) {
            changed = false;
            for (int s : order) {
                if (!sel[s]) continue;
                bool can = true;
                for (int e : elemsOfSet[s]) {
                    if (cover[e] <= 1) { can = false; break; }
                }
                if (can) {
                    sel[s] = 0;
                    for (int e : elemsOfSet[s]) cover[e]--;
                    changed = true;
                }
            }
        }
    };

    auto improve1to1 = [&](vector<char> &sel) {
        bool improvedAny = false;
        vector<int> cover(n, 0);
        for (int s = 0; s < m; ++s) if (sel[s]) {
            for (int e : elemsOfSet[s]) cover[e]++;
        }
        vector<int> selectedIdx;
        selectedIdx.reserve(m);
        for (int s = 0; s < m; ++s) if (sel[s]) selectedIdx.push_back(s);
        sort(selectedIdx.begin(), selectedIdx.end(), [&](int a, int b){
            if (cost[a] != cost[b]) return cost[a] > cost[b];
            return elemsOfSet[a].size() > elemsOfSet[b].size();
        });
        int Wloc = W;
        vector<uint64_t> Ubits(Wloc);
        for (int idx = 0; idx < (int)selectedIdx.size(); ++idx) {
            int s = selectedIdx[idx];
            if (!sel[s]) continue; // might have been removed
            // Compute unique elements covered only by s
            bool hasUnique = false;
            for (int w = 0; w < Wloc; ++w) Ubits[w] = 0;
            int minnDeg = INT_MAX, eStar = -1;
            for (int e : elemsOfSet[s]) {
                if (cover[e] == 1) {
                    Ubits[e >> 6] |= (1ULL << (e & 63));
                    hasUnique = true;
                    int deg = (int)setsOfElem[e].size();
                    if (deg < minnDeg) { minnDeg = deg; eStar = e; }
                }
            }
            if (!hasUnique) {
                // redundant; can remove
                sel[s] = 0;
                for (int e : elemsOfSet[s]) cover[e]--;
                improvedAny = true;
                continue;
            }
            if (eStar == -1) continue;

            long long bestCost = LLONG_MAX;
            int bestSet = -1;
            for (int cand : setsOfElem[eStar]) {
                if (cand == s) continue;
                if (sel[cand]) continue;
                if (cost[cand] >= cost[s]) continue; // only if strictly better
                bool ok = true;
                for (int w = 0; w < Wloc; ++w) {
                    uint64_t miss = Ubits[w] & ~setBits[cand][w];
                    if (miss) { ok = false; break; }
                }
                if (ok) {
                    if (cost[cand] < bestCost) {
                        bestCost = cost[cand];
                        bestSet = cand;
                    }
                }
            }
            if (bestSet != -1) {
                // perform swap
                sel[s] = 0;
                for (int e : elemsOfSet[s]) cover[e]--;
                sel[bestSet] = 1;
                for (int e : elemsOfSet[bestSet]) cover[e]++;
                improvedAny = true;
            }
        }
        return improvedAny;
    };

    auto run_greedy = [&](double alpha, double noiseLevel, mt19937_64 &rng) -> vector<char> {
        vector<double> weight(n, 1.0);
        for (int e = 0; e < n; ++e) {
            int d = (int)setsOfElem[e].size();
            if (d <= 0) weight[e] = 1.0;
            else if (alpha == 0.0) weight[e] = 1.0;
            else weight[e] = pow(1.0 / (double)d, alpha);
        }

        vector<double> benefit(m, 0.0);
        vector<double> costAdj(m);
        uniform_real_distribution<double> urd(0.0, 1.0);
        for (int s = 0; s < m; ++s) {
            double b = 0.0;
            for (int e : elemsOfSet[s]) b += weight[e];
            benefit[s] = b;
            double noise = noiseLevel > 0 ? (1.0 + noiseLevel * urd(rng)) : 1.0;
            costAdj[s] = (double)cost[s] * noise;
        }

        vector<char> selected(m, 0);
        vector<int> cover(n, 0);
        int uncovered = n;

        priority_queue<HeapNode> pq;
        for (int s = 0; s < m; ++s) {
            if (benefit[s] > 0.0) {
                pq.push({costAdj[s] / benefit[s], s, benefit[s]});
            }
        }

        auto add_set = [&](int s) {
            if (selected[s]) return;
            selected[s] = 1;
            for (int e : elemsOfSet[s]) {
                if (cover[e] == 0) {
                    // When covering e for the first time, reduce benefit of all sets containing e
                    for (int t : setsOfElem[e]) {
                        benefit[t] -= weight[e];
                        if (benefit[t] < 0) benefit[t] = 0;
                    }
                    uncovered--;
                }
                cover[e]++;
            }
        };

        // Greedy selection
        while (uncovered > 0) {
            bool picked = false;
            while (!pq.empty()) {
                auto nd = pq.top(); pq.pop();
                int s = nd.id;
                if (selected[s]) continue;
                if (benefit[s] <= 0.0) continue;
                if (nd.benefitAtInsert != benefit[s]) {
                    pq.push({costAdj[s] / max(benefit[s], 1e-18), s, benefit[s]});
                    continue;
                }
                add_set(s);
                picked = true;
                break;
            }
            if (!picked) {
                // Fallback: pick cheapest set covering any uncovered element
                int ePick = -1;
                for (int e = 0; e < n; ++e) if (cover[e] == 0) { ePick = e; break; }
                if (ePick == -1) break; // should not happen
                int bestSet = -1;
                long long bestC = LLONG_MAX;
                for (int s : setsOfElem[ePick]) {
                    if (selected[s]) continue;
                    if (cost[s] < bestC) { bestC = cost[s]; bestSet = s; }
                }
                if (bestSet == -1) {
                    // cannot cover this element; impossible instance
                    break;
                }
                add_set(bestSet);
                if (benefit[bestSet] > 0) {
                    pq.push({costAdj[bestSet] / max(benefit[bestSet], 1e-18), bestSet, benefit[bestSet]});
                }
            }
        }

        return selected;
    };

    // Multi-start with time budget
    auto startTime = chrono::steady_clock::now();
    long long timeBudgetMs = 1800; // modest budget to be safe
    vector<double> alphas = {0.0, 0.25, 0.5, 0.75, 1.0};
    vector<double> noises = {0.0, 0.02, 0.05, 0.1, 0.2};
    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<char> bestSel(m, 0);
    long long bestCost = (1LL<<62);
    bool bestValid = false;

    // One deterministic run first
    {
        vector<char> sel = run_greedy(0.5, 0.0, rng);
        prune(sel);
        while (improve1to1(sel)) {
            prune(sel);
        }
        if (is_valid_cover(sel)) {
            long long cst = compute_cost(sel);
            if (cst < bestCost) { bestCost = cst; bestSel = sel; bestValid = true; }
        }
    }

    for (double alpha : alphas) {
        for (double noise : noises) {
            auto now = chrono::steady_clock::now();
            long long elapsed = chrono::duration_cast<chrono::milliseconds>(now - startTime).count();
            if (elapsed > timeBudgetMs) break;

            vector<char> sel = run_greedy(alpha, noise, rng);
            prune(sel);
            while (improve1to1(sel)) {
                prune(sel);
            }
            if (is_valid_cover(sel)) {
                long long cst = compute_cost(sel);
                if (cst < bestCost || !bestValid) { bestCost = cst; bestSel = sel; bestValid = true; }
            }
        }
    }

    if (!bestValid) {
        // Fallback: cover each element by cheapest set covering it
        vector<char> sel(m, 0);
        for (int e = 0; e < n; ++e) {
            int bestSet = -1;
            long long bestC = LLONG_MAX;
            for (int s : setsOfElem[e]) {
                if (cost[s] < bestC) { bestC = cost[s]; bestSet = s; }
            }
            if (bestSet != -1) sel[bestSet] = 1;
        }
        prune(sel);
        if (is_valid_cover(sel)) {
            bestSel = sel;
            bestCost = compute_cost(sel);
            bestValid = true;
        } else {
            // As a last resort, output empty
            cout << 0 << "\n\n";
            return 0;
        }
    }

    vector<int> ans;
    ans.reserve(m);
    for (int i = 0; i < m; ++i) if (bestSel[i]) ans.push_back(i + 1);

    cout << (int)ans.size() << "\n";
    for (int i = 0; i < (int)ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}