#include <bits/stdc++.h>
using namespace std;

struct Solution {
    vector<int> sets; // 0-based indices
    long long cost = (1LL<<62);
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<long long> cost(m);
    for (int i = 0; i < m; ++i) cin >> cost[i];

    vector<vector<int>> setsOfElement(n);
    long long totalIncidence = 0;
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        setsOfElement[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int a; cin >> a;
            --a; // convert to 0-based
            if (a >= 0 && a < m) {
                setsOfElement[i].push_back(a);
                ++totalIncidence;
            }
        }
    }

    // Build elementsOfSet
    vector<vector<int>> elementsOfSet(m);
    for (int e = 0; e < n; ++e) {
        for (int s : setsOfElement[e]) elementsOfSet[s].push_back(e);
    }

    // Check for impossible elements (no sets containing them)
    for (int e = 0; e < n; ++e) {
        if (setsOfElement[e].empty()) {
            cout << 0 << "\n\n";
            return 0;
        }
    }

    // Precompute inverse costs
    const double INF_D = 1e300;
    vector<double> invCost(m);
    for (int i = 0; i < m; ++i) invCost[i] = (cost[i] == 0 ? 1e18 : 1.0 / (double)cost[i]);

    // Frequencies per element
    vector<int> freq(n);
    for (int e = 0; e < n; ++e) freq[e] = (int)setsOfElement[e].size();

    // Random generator
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto greedy_with_weights = [&](const vector<double>& w) -> Solution {
        vector<double> score(m, 0.0);
        score.shrink_to_fit();
        // Initialize score[s] = sum of weights of elements in set s
        for (int s = 0; s < m; ++s) {
            double sumw = 0.0;
            for (int e : elementsOfSet[s]) sumw += w[e];
            score[s] = sumw;
        }

        vector<char> selected(m, 0);
        vector<char> covered(n, 0);
        int uncovered = n;

        vector<int> chosen;
        chosen.reserve(n);

        // Greedy selection
        while (uncovered > 0) {
            int bestSet = -1;
            double bestVal = -1.0;

            for (int s = 0; s < m; ++s) {
                if (selected[s]) continue;
                double sc = score[s];
                if (sc <= 1e-15) continue;
                double val = sc * invCost[s]; // effectively sc / cost
                if (val > bestVal) {
                    bestVal = val;
                    bestSet = s;
                }
            }

            if (bestSet == -1) {
                // Fallback: pick cheapest set for any uncovered element
                bool progress = false;
                for (int e = 0; e < n && uncovered > 0; ++e) {
                    if (!covered[e]) {
                        int best = -1;
                        long long bestC = (1LL<<62);
                        for (int s : setsOfElement[e]) {
                            if (!selected[s] && cost[s] < bestC) {
                                bestC = cost[s];
                                best = s;
                            }
                        }
                        if (best != -1) {
                            bestSet = best;
                            progress = true;
                            break;
                        }
                    }
                }
                if (!progress) break; // impossible
            }

            if (bestSet == -1) break;

            selected[bestSet] = 1;
            chosen.push_back(bestSet);

            // Update scores and covered
            for (int e : elementsOfSet[bestSet]) {
                if (!covered[e]) {
                    covered[e] = 1;
                    --uncovered;
                    double we = w[e];
                    // reduce the score for all sets containing e
                    for (int s : setsOfElement[e]) {
                        if (!selected[s]) score[s] -= we;
                    }
                }
            }
        }

        // If still uncovered, impossible; return large cost empty
        for (int e = 0; e < n; ++e) {
            if (!covered[e]) {
                return Solution{};
            }
        }

        // Redundancy elimination (reverse-delete), prefer removing expensive sets first
        vector<int> order = chosen;
        sort(order.begin(), order.end(), [&](int a, int b){
            if (cost[a] != cost[b]) return cost[a] > cost[b];
            return elementsOfSet[a].size() > elementsOfSet[b].size();
        });
        vector<int> cnt(n, 0);
        for (int s : chosen) {
            for (int e : elementsOfSet[s]) cnt[e]++;
        }

        vector<char> keep(m, 0);
        for (int s : chosen) keep[s] = 1;
        bool changed = true;
        // Iterate until no more removals
        while (changed) {
            changed = false;
            for (int s : order) {
                if (!keep[s]) continue;
                bool canRemove = true;
                for (int e : elementsOfSet[s]) {
                    if (cnt[e] <= 1) { canRemove = false; break; }
                }
                if (canRemove) {
                    keep[s] = 0;
                    changed = true;
                    for (int e : elementsOfSet[s]) cnt[e]--;
                }
            }
        }

        vector<int> finalSel;
        finalSel.reserve(chosen.size());
        long long totalCost = 0;
        for (int s : chosen) {
            if (keep[s]) {
                finalSel.push_back(s);
                totalCost += cost[s];
            }
        }

        // Safety: ensure all covered
        fill(covered.begin(), covered.end(), 0);
        for (int s : finalSel) {
            for (int e : elementsOfSet[s]) covered[e] = 1;
        }
        for (int e = 0; e < n; ++e) {
            if (!covered[e]) {
                // add cheapest set for this element
                int best = -1;
                long long bestC = (1LL<<62);
                for (int s : setsOfElement[e]) {
                    if (cost[s] < bestC) {
                        bestC = cost[s]; best = s;
                    }
                }
                if (best != -1) {
                    finalSel.push_back(best);
                    totalCost += cost[best];
                    for (int ee : elementsOfSet[best]) covered[ee] = 1;
                }
            }
        }

        // Final check
        for (int e = 0; e < n; ++e) {
            if (!covered[e]) {
                return Solution{};
            }
        }

        Solution sol;
        sol.sets = move(finalSel);
        sol.cost = totalCost;
        return sol;
    };

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(9500);

    // Initial deterministic weights
    vector<double> weights(n, 1.0);
    for (int e = 0; e < n; ++e) {
        weights[e] = 1.0 / max(1, freq[e]);
    }

    Solution best = greedy_with_weights(weights);
    if (best.sets.empty()) {
        // Fallback: simple heuristic - for each element, pick cheapest set
        vector<char> covered(n, 0);
        vector<int> cnt(n, 0);
        vector<int> sel;
        vector<char> picked(m, 0);
        long long totC = 0;
        for (int e = 0; e < n; ++e) {
            int bestS = -1;
            long long bestC = (1LL<<62);
            for (int s : setsOfElement[e]) {
                if (cost[s] < bestC) { bestC = cost[s]; bestS = s; }
            }
            if (bestS != -1 && !picked[bestS]) {
                picked[bestS] = 1;
                sel.push_back(bestS);
                totC += cost[bestS];
                for (int ee : elementsOfSet[bestS]) covered[ee] = 1;
            }
        }
        bool ok = true;
        for (int e = 0; e < n; ++e) if (!covered[e]) ok = false;
        if (ok) {
            best.sets = sel;
            best.cost = totC;
        } else {
            cout << 0 << "\n\n";
            return 0;
        }
    }

    uniform_real_distribution<double> noiseDist(0.85, 1.15);
    uniform_real_distribution<double> alphaDist(0.5, 1.5);

    // Iterative randomized greedy within time budget
    int iter = 0;
    while (chrono::steady_clock::now() < deadline) {
        vector<double> w(n);
        double alpha = alphaDist(rng);
        for (int e = 0; e < n; ++e) {
            w[e] = pow((double)max(1, freq[e]), -alpha) * noiseDist(rng);
        }
        Solution sol = greedy_with_weights(w);
        if (!sol.sets.empty() && sol.cost < best.cost) {
            best = move(sol);
        }
        ++iter;
    }

    // Prepare output: sort set ids ascending and convert to 1-based
    sort(best.sets.begin(), best.sets.end());
    cout << (int)best.sets.size() << "\n";
    for (size_t i = 0; i < best.sets.size(); ++i) {
        if (i) cout << ' ';
        cout << (best.sets[i] + 1);
    }
    cout << "\n";
    return 0;
}