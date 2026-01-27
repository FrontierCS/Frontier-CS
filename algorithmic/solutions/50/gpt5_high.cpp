#include <bits/stdc++.h>
using namespace std;

static const int MAXB = 512;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getch();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getch();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getch(); }
        for (; c >= '0' && c <= '9'; c = getch())
            val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
} In;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!In.readInt(n)) return 0;
    In.readInt(m);

    vector<long long> cost(m + 1, 0);
    for (int i = 1; i <= m; i++) In.readInt(cost[i]);

    vector<vector<int>> setElems(m + 1);
    vector<vector<int>> elemSets(n + 1);
    vector<int> deg(n + 1, 0);

    for (int i = 1; i <= n; i++) {
        int k; In.readInt(k);
        deg[i] = k;
        for (int j = 0; j < k; j++) {
            int s; In.readInt(s);
            if (s < 1 || s > m) continue;
            setElems[s].push_back(i);
            elemSets[i].push_back(s);
        }
    }

    // If any element has no set, impossible; print 0
    for (int i = 1; i <= n; i++) {
        if (elemSets[i].empty()) {
            cout << 0 << "\n\n";
            return 0;
        }
    }

    // Build bitsets for dominance checks
    vector<bitset<MAXB>> setBits(m + 1);
    for (int s = 1; s <= m; s++) {
        for (int e : setElems[s]) {
            if (e >= 1 && e <= n) setBits[s].set(e - 1);
        }
    }

    vector<char> disabled(m + 1, 0);
    // Disable empty sets (no elements)
    for (int s = 1; s <= m; s++) {
        if (setElems[s].empty()) disabled[s] = 1;
    }

    // Dominance elimination: if S_i subset of S_j and cost_i >= cost_j, disable i
    vector<int> setSize(m + 1, 0);
    for (int s = 1; s <= m; s++) setSize[s] = (int)setElems[s].size();

    for (int i = 1; i <= m; i++) {
        if (disabled[i]) continue;
        for (int j = 1; j <= m; j++) {
            if (i == j || disabled[j]) continue;
            if (setSize[i] > setSize[j]) continue;
            if (cost[i] < cost[j]) continue; // need cost[i] >= cost[j]
            // subset check: i subset of j?
            // i subset j <=> (i & ~j) == 0
            // quick skip if size condition impossible
            bitset<MAXB> tmp = setBits[i] & (~setBits[j]);
            if (tmp.none()) { // i is subset of j
                disabled[i] = 1;
                break;
            }
        }
    }

    // Preselect forced sets: elements with degree 1
    vector<char> forced(m + 1, 0);
    for (int e = 1; e <= n; e++) {
        if ((int)elemSets[e].size() == 1) {
            int s = elemSets[e][0];
            if (!disabled[s]) forced[s] = 1;
        }
    }

    // Prepare common data for runs
    vector<int> initCount(m + 1, 0);
    for (int s = 1; s <= m; s++) initCount[s] = (int)setElems[s].size();

    // Random engine
    std::mt19937_64 rng(std::chrono::high_resolution_clock::now().time_since_epoch().count());
    auto randDouble = [&]() -> double {
        return std::uniform_real_distribution<double>(0.0, 1.0)(rng);
    };
    auto randInt = [&](int l, int r) -> int {
        return std::uniform_int_distribution<int>(l, r)(rng);
    };

    // Greedy run function as lambda
    auto run_once = [&](double epsilon, int topK) {
        vector<int> count = initCount;
        vector<char> selected(m + 1, 0);
        vector<char> covered(n + 1, 0);
        int uncovered = n;

        // apply forced selection
        vector<int> chosen;
        for (int s = 1; s <= m; s++) {
            if (disabled[s]) continue;
            if (forced[s]) {
                selected[s] = 1;
                chosen.push_back(s);
                for (int e : setElems[s]) {
                    if (!covered[e]) {
                        covered[e] = 1;
                        --uncovered;
                        for (int t : elemSets[e]) {
                            if (count[t] > 0) count[t]--;
                        }
                    }
                }
            }
        }

        // main loop
        while (uncovered > 0) {
            // pick candidate
            // topK minimal ratios
            const int K = max(1, min(topK, m));
            vector<double> bestScore(K, numeric_limits<double>::infinity());
            vector<int> bestId(K, -1);

            for (int s = 1; s <= m; s++) {
                if (disabled[s] || selected[s]) continue;
                int b = count[s];
                if (b <= 0) continue;
                double r = (double)cost[s] / (double)b;
                if (epsilon > 0) r *= (1.0 + epsilon * randDouble());
                // insertion into topK
                for (int k = 0; k < K; k++) {
                    if (r < bestScore[k]) {
                        for (int t = K - 1; t > k; t--) {
                            bestScore[t] = bestScore[t - 1];
                            bestId[t] = bestId[t - 1];
                        }
                        bestScore[k] = r;
                        bestId[k] = s;
                        break;
                    }
                }
            }

            int pick = -1;
            // handle no candidates (shouldn't happen if instance solvable)
            int validCnt = 0;
            while (validCnt < (int)bestId.size() && bestId[validCnt] != -1) validCnt++;
            if (validCnt == 0) {
                // try to pick any set that covers at least one uncovered element
                double bestR = numeric_limits<double>::infinity();
                for (int s = 1; s <= m; s++) {
                    if (disabled[s] || selected[s]) continue;
                    int b = count[s];
                    if (b <= 0) continue;
                    double r = (double)cost[s] / (double)b;
                    if (r < bestR) {
                        bestR = r;
                        pick = s;
                    }
                }
                if (pick == -1) break; // cannot progress
            } else {
                if (validCnt == 1) pick = bestId[0];
                else pick = bestId[randInt(0, validCnt - 1)];
            }

            if (pick == -1) break;
            selected[pick] = 1;
            chosen.push_back(pick);
            for (int e : setElems[pick]) {
                if (!covered[e]) {
                    covered[e] = 1;
                    --uncovered;
                    for (int t : elemSets[e]) {
                        if (count[t] > 0) count[t]--;
                    }
                }
            }
        }

        // If unsolved, return empty to signal failure
        if (any_of(begin(forced), end(forced), [&](char f) { return false; }) ) {
            // dummy line to silence -Wunused-lambda-capture warning in some compilers
            ;
        }
        bool allCovered = true;
        if (true) {
            // check coverage
            vector<char> cov(n + 1, 0);
            for (int s : chosen) {
                for (int e : setElems[s]) cov[e] = 1;
            }
            for (int e = 1; e <= n; e++) {
                if (!cov[e]) { allCovered = false; break; }
            }
        }
        if (!allCovered) {
            // Fallback: try simple deterministic greedy until covered
            vector<int> count2 = initCount;
            vector<char> selected2(m + 1, 0);
            vector<char> covered2(n + 1, 0);
            int uncovered2 = n;
            // forced
            for (int s = 1; s <= m; s++) {
                if (disabled[s]) continue;
                if (forced[s]) {
                    selected2[s] = 1;
                    for (int e : setElems[s]) {
                        if (!covered2[e]) {
                            covered2[e] = 1;
                            --uncovered2;
                            for (int t : elemSets[e]) if (count2[t] > 0) count2[t]--;
                        }
                    }
                }
            }
            vector<int> chosen2;
            for (int s = 1; s <= m; s++) if (selected2[s]) chosen2.push_back(s);
            while (uncovered2 > 0) {
                int pick2 = -1;
                double bestR = numeric_limits<double>::infinity();
                for (int s = 1; s <= m; s++) {
                    if (disabled[s] || selected2[s]) continue;
                    int b = count2[s];
                    if (b <= 0) continue;
                    double r = (double)cost[s] / (double)b;
                    if (r < bestR) { bestR = r; pick2 = s; }
                }
                if (pick2 == -1) break;
                selected2[pick2] = 1;
                chosen2.push_back(pick2);
                for (int e : setElems[pick2]) {
                    if (!covered2[e]) {
                        covered2[e] = 1;
                        --uncovered2;
                        for (int t : elemSets[e]) if (count2[t] > 0) count2[t]--;
                    }
                }
            }
            bool ok2 = true;
            for (int e = 1; e <= n; e++) if (!covered2[e]) { ok2 = false; break; }
            if (!ok2) {
                // Give up
                chosen.clear();
            } else {
                chosen.swap(chosen2);
            }
        }

        // Prune redundant sets
        if (!chosen.empty()) {
            vector<int> coverCnt(n + 1, 0);
            for (int s : chosen) for (int e : setElems[s]) coverCnt[e]++;
            // Sort chosen by decreasing "cost per size", prioritize removing expensive sets first
            vector<int> order = chosen;
            sort(order.begin(), order.end(), [&](int a, int b) {
                double ra = (setElems[a].empty() ? 1e100 : (double)cost[a] / (double)setElems[a].size());
                double rb = (setElems[b].empty() ? 1e100 : (double)cost[b] / (double)setElems[b].size());
                if (fabs(ra - rb) > 1e-12) return ra > rb;
                if (cost[a] != cost[b]) return cost[a] > cost[b];
                return a < b;
            });
            vector<char> keep(m + 1, 0);
            for (int s : chosen) keep[s] = 1;
            for (int s : order) {
                bool removable = true;
                for (int e : setElems[s]) {
                    if (coverCnt[e] <= 1) { removable = false; break; }
                }
                if (removable) {
                    keep[s] = 0;
                    for (int e : setElems[s]) coverCnt[e]--;
                }
            }
            vector<int> newChosen;
            newChosen.reserve(chosen.size());
            for (int s : chosen) if (keep[s]) newChosen.push_back(s);
            chosen.swap(newChosen);
        }

        // Return result
        return chosen;
    };

    auto evaluate_cost = [&](const vector<int>& S) -> long long {
        long long sum = 0;
        for (int s : S) sum += cost[s];
        return sum;
    };

    auto is_valid = [&](const vector<int>& S) -> bool {
        vector<char> cov(n + 1, 0);
        for (int s : S) {
            for (int e : setElems[s]) cov[e] = 1;
        }
        for (int e = 1; e <= n; e++) if (!cov[e]) return false;
        return true;
    };

    // Baseline deterministic run
    vector<int> best = run_once(0.0, 1);
    long long bestCost = (best.empty() ? (long long)4e18 : evaluate_cost(best));
    if (best.empty()) {
        // Fallback: naive covering by arbitrarily adding sets until covered
        vector<char> covered(n + 1, 0);
        int uncovered = n;
        vector<int> pick;
        vector<int> count = initCount;
        vector<char> selected(m + 1, 0);
        while (uncovered > 0) {
            int sel = -1;
            int mx = -1;
            // pick set that covers the most uncovered elements, tie by minimal cost
            for (int s = 1; s <= m; s++) {
                if (disabled[s] || selected[s]) continue;
                int b = count[s];
                if (b > mx || (b == mx && b > 0 && cost[s] < cost[sel])) {
                    sel = s; mx = b;
                }
            }
            if (sel == -1) break;
            selected[sel] = 1;
            pick.push_back(sel);
            for (int e : setElems[sel]) {
                if (!covered[e]) {
                    covered[e] = 1; --uncovered;
                    for (int t : elemSets[e]) if (count[t] > 0) count[t]--;
                }
            }
        }
        if (is_valid(pick)) {
            best = pick;
            bestCost = evaluate_cost(best);
        } else {
            // if still invalid, select all sets (last resort)
            best.clear();
            for (int s = 1; s <= m; s++) if (!disabled[s] && !setElems[s].empty()) best.push_back(s);
            if (!is_valid(best)) {
                cout << 0 << "\n\n";
                return 0;
            }
            bestCost = evaluate_cost(best);
        }
    }

    // Multi-start with time budget
    auto t_start = chrono::high_resolution_clock::now();
    auto elapsed_sec = [&]() -> double {
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - t_start).count();
    };

    double timeBudget = 9.5; // seconds
    int iterations = 0;
    while (elapsed_sec() < timeBudget) {
        double eps = std::uniform_real_distribution<double>(0.0, 0.35)(rng);
        int topK = std::uniform_int_distribution<int>(1, 12)(rng);
        auto cand = run_once(eps, topK);
        if (!cand.empty()) {
            long long c = evaluate_cost(cand);
            if (c < bestCost) {
                bestCost = c;
                best.swap(cand);
            }
        }
        iterations++;
    }

    // Final prune once more
    if (!best.empty()) {
        vector<int> coverCnt(n + 1, 0);
        for (int s : best) for (int e : setElems[s]) coverCnt[e]++;
        vector<int> order = best;
        sort(order.begin(), order.end(), [&](int a, int b) {
            double ra = (setElems[a].empty() ? 1e100 : (double)cost[a] / (double)setElems[a].size());
            double rb = (setElems[b].empty() ? 1e100 : (double)cost[b] / (double)setElems[b].size());
            if (fabs(ra - rb) > 1e-12) return ra > rb;
            if (cost[a] != cost[b]) return cost[a] > cost[b];
            return a < b;
        });
        vector<char> keep(m + 1, 0);
        for (int s : best) keep[s] = 1;
        for (int s : order) {
            bool removable = true;
            for (int e : setElems[s]) {
                if (coverCnt[e] <= 1) { removable = false; break; }
            }
            if (removable) {
                keep[s] = 0;
                for (int e : setElems[s]) coverCnt[e]--;
            }
        }
        vector<int> reduced;
        for (int s : best) if (keep[s]) reduced.push_back(s);
        if (is_valid(reduced)) {
            long long c = evaluate_cost(reduced);
            if (c <= bestCost) {
                bestCost = c;
                best.swap(reduced);
            }
        }
    }

    // Sort ids for stable output
    sort(best.begin(), best.end());
    cout << best.size() << "\n";
    for (size_t i = 0; i < best.size(); i++) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << "\n";
    return 0;
}