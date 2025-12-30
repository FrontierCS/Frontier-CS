#include <bits/stdc++.h>
using namespace std;

struct Instance {
    int n, m;
    vector<long long> cost;                // 1..m
    vector<vector<int>> setsOfElem;        // 1..n: list of set ids containing element i
    vector<vector<int>> elemsOfSet;        // 1..m: list of element ids in set j
};

struct Solution {
    vector<char> chosen;   // 1..m
    vector<int> cover;     // 1..n counts
    long long totalCost = 0;
};

static inline uint64_t now_us() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

struct GreedyBuilder {
    const Instance* ins;
    mt19937_64 rng;
    double noise_min = 0.9, noise_max = 1.1;

    GreedyBuilder(const Instance* instance, uint64_t seed) : ins(instance), rng(seed) {}

    Solution build(double noiseLevel = 0.15) {
        int n = ins->n, m = ins->m;
        Solution sol;
        sol.chosen.assign(m + 1, 0);
        sol.cover.assign(n + 1, 0);
        sol.totalCost = 0;

        vector<int> benefit(m + 1, 0);
        vector<int> stamp(m + 1, 0);
        vector<double> multiplier(m + 1, 1.0);

        uniform_real_distribution<double> dist(1.0 - noiseLevel, 1.0 + noiseLevel);
        for (int j = 1; j <= m; ++j) {
            benefit[j] = (int)ins->elemsOfSet[j].size();
            if (noiseLevel > 1e-12) multiplier[j] = dist(rng);
        }

        struct Node {
            double key;
            int id;
            int stamp;
            bool operator>(const Node& other) const { return key > other.key; }
        };
        priority_queue<Node, vector<Node>, greater<Node>> pq;

        for (int j = 1; j <= m; ++j) {
            if (benefit[j] > 0) {
                double key = (double)ins->cost[j] * multiplier[j] / (double)benefit[j];
                pq.push({key, j, stamp[j]});
            }
        }

        int uncovered = n;

        while (uncovered > 0) {
            // Ensure there exists a set covering any uncovered element
            if (pq.empty()) {
                // fallback: try to explicitly add any set that covers an uncovered element
                // pick the cheapest such set
                long long bestC = LLONG_MAX;
                int bestJ = -1;
                for (int j = 1; j <= m; ++j) if (!sol.chosen[j]) {
                    bool coversNew = false;
                    for (int e : ins->elemsOfSet[j]) if (sol.cover[e] == 0) { coversNew = true; break; }
                    if (coversNew && ins->cost[j] < bestC) { bestC = ins->cost[j]; bestJ = j; }
                }
                if (bestJ == -1) break; // no solution possible; break
                // add bestJ
                sol.chosen[bestJ] = 1;
                sol.totalCost += ins->cost[bestJ];
                for (int e : ins->elemsOfSet[bestJ]) {
                    if (sol.cover[e] == 0) {
                        // update benefits of sets containing e
                        for (int t : ins->setsOfElem[e]) {
                            if (!sol.chosen[t] && benefit[t] > 0) {
                                benefit[t]--;
                                stamp[t]++;
                                if (benefit[t] > 0) {
                                    double key = (double)ins->cost[t] * multiplier[t] / (double)benefit[t];
                                    pq.push({key, t, stamp[t]});
                                }
                            }
                        }
                        --uncovered;
                    }
                    sol.cover[e]++;
                }
                continue;
            }

            Node nd = pq.top(); pq.pop();
            int j = nd.id;
            if (sol.chosen[j]) continue;
            if (nd.stamp != stamp[j]) continue;
            if (benefit[j] <= 0) continue;

            // pick j
            sol.chosen[j] = 1;
            sol.totalCost += ins->cost[j];

            for (int e : ins->elemsOfSet[j]) {
                if (sol.cover[e] == 0) {
                    for (int t : ins->setsOfElem[e]) {
                        if (!sol.chosen[t] && benefit[t] > 0) {
                            benefit[t]--;
                            stamp[t]++;
                            if (benefit[t] > 0) {
                                double key = (double)ins->cost[t] * multiplier[t] / (double)benefit[t];
                                pq.push({key, t, stamp[t]});
                            }
                        }
                    }
                    --uncovered;
                }
                sol.cover[e]++;
            }
        }

        return sol;
    }
};

static inline void pruneRedundant(const Instance& ins, Solution& sol) {
    int m = ins.m, n = ins.n;
    vector<int> order;
    order.reserve(m);
    for (int j = 1; j <= m; ++j) if (sol.chosen[j]) order.push_back(j);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (ins.cost[a] != ins.cost[b]) return ins.cost[a] > ins.cost[b];
        return ins.elemsOfSet[a].size() > ins.elemsOfSet[b].size();
    });

    bool changed = true;
    int loops = 0;
    while (changed && loops < 3) {
        changed = false;
        ++loops;
        for (int j : order) {
            if (!sol.chosen[j]) continue;
            bool red = true;
            const auto& elems = ins.elemsOfSet[j];
            for (int e : elems) {
                if (sol.cover[e] <= 1) { red = false; break; }
            }
            if (red) {
                sol.chosen[j] = 0;
                sol.totalCost -= ins.cost[j];
                for (int e : elems) sol.cover[e]--;
                changed = true;
            }
        }
    }
}

static inline bool localImproveOnce(const Instance& ins, Solution& sol, mt19937_64& rng) {
    int m = ins.m, n = ins.n;
    vector<int> chosenList;
    chosenList.reserve(m);
    for (int j = 1; j <= m; ++j) if (sol.chosen[j]) chosenList.push_back(j);
    sort(chosenList.begin(), chosenList.end(), [&](int a, int b){
        if (ins.cost[a] != ins.cost[b]) return ins.cost[a] > ins.cost[b];
        return ins.elemsOfSet[a].size() > ins.elemsOfSet[b].size();
    });

    vector<int> nonChosen;
    nonChosen.reserve(m);
    for (int j = 1; j <= m; ++j) if (!sol.chosen[j]) nonChosen.push_back(j);

    // randomize scan order to diversify
    shuffle(nonChosen.begin(), nonChosen.end(), rng);

    long long bestGain = 0;
    int bestAdd = -1;
    vector<int> bestRemove;

    vector<int> tempCover(ins.n + 1);

    for (int s : nonChosen) {
        const auto& elemsS = ins.elemsOfSet[s];
        if (elemsS.empty()) continue; // no benefit
        tempCover = sol.cover;
        for (int e : elemsS) tempCover[e]++;

        long long savings = 0;
        vector<int> toRemove;
        toRemove.reserve(chosenList.size());

        for (int c : chosenList) {
            if (!sol.chosen[c]) continue; // might have been removed from previous iterations but not here
            bool canRem = true;
            for (int e : ins.elemsOfSet[c]) {
                if (tempCover[e] <= 1) { canRem = false; break; }
            }
            if (canRem) {
                toRemove.push_back(c);
                savings += ins.cost[c];
                for (int e : ins.elemsOfSet[c]) tempCover[e]--;
            }
        }

        long long gain = savings - ins.cost[s];
        if (gain > bestGain) {
            bestGain = gain;
            bestAdd = s;
            bestRemove = std::move(toRemove);
        }
    }

    if (bestGain > 0 && bestAdd != -1) {
        sol.chosen[bestAdd] = 1;
        sol.totalCost += ins.cost[bestAdd];
        for (int e : ins.elemsOfSet[bestAdd]) sol.cover[e]++;

        for (int c : bestRemove) if (sol.chosen[c]) {
            sol.chosen[c] = 0;
            sol.totalCost -= ins.cost[c];
            for (int e : ins.elemsOfSet[c]) sol.cover[e]--;
        }
        // Further prune after swap
        pruneRedundant(ins, sol);
        return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Instance ins;
    if (!(cin >> ins.n >> ins.m)) {
        return 0;
    }
    ins.cost.assign(ins.m + 1, 0);
    for (int j = 1; j <= ins.m; ++j) {
        long long c; cin >> c; ins.cost[j] = c;
    }
    ins.setsOfElem.assign(ins.n + 1, {});
    ins.elemsOfSet.assign(ins.m + 1, {});
    for (int i = 1; i <= ins.n; ++i) {
        int k; cin >> k;
        ins.setsOfElem[i].reserve(k);
        for (int t = 0; t < k; ++t) {
            int a; cin >> a;
            if (a >= 1 && a <= ins.m) {
                ins.setsOfElem[i].push_back(a);
                ins.elemsOfSet[a].push_back(i);
            }
        }
    }

    uint64_t start_us = now_us();
    uint64_t time_limit_us = 9500000; // 9.5 seconds

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    Solution bestSol;
    bestSol.chosen.assign(ins.m + 1, 0);
    bestSol.cover.assign(ins.n + 1, 0);
    bestSol.totalCost = (1LL<<62);

    // Perform multiple runs with GRASP-like noise and local improvements
    int run = 0;
    while (now_us() - start_us < time_limit_us) {
        double noiseLevel = 0.05 + 0.20 * ((run % 7) / 6.0); // vary noise
        GreedyBuilder builder(&ins, rng());
        Solution sol = builder.build(noiseLevel);

        // If solution incomplete, try a fallback greedy without noise
        bool complete = true;
        for (int i = 1; i <= ins.n; ++i) if (sol.cover[i] <= 0) { complete = false; break; }
        if (!complete) {
            GreedyBuilder builder2(&ins, rng());
            sol = builder2.build(0.0);
        }

        // Ensure coverage (attempt fill uncovered if any)
        for (int i = 1; i <= ins.n; ++i) {
            if (sol.cover[i] == 0) {
                // add cheapest set covering i
                long long bestC = LLONG_MAX;
                int bestJ = -1;
                for (int s : ins.setsOfElem[i]) {
                    if (!sol.chosen[s] && ins.cost[s] < bestC) {
                        bestC = ins.cost[s];
                        bestJ = s;
                    }
                }
                if (bestJ != -1) {
                    sol.chosen[bestJ] = 1;
                    sol.totalCost += ins.cost[bestJ];
                    for (int e : ins.elemsOfSet[bestJ]) sol.cover[e]++;
                }
            }
        }

        pruneRedundant(ins, sol);

        // Local improvement loop within time budget
        while (now_us() - start_us < time_limit_us) {
            bool improved = localImproveOnce(ins, sol, rng);
            if (!improved) break;
        }

        if (sol.totalCost < bestSol.totalCost) {
            bestSol = sol;
        }

        run++;
        if (run > 50 && now_us() - start_us > time_limit_us * 0.9) break;
    }

    // Output best solution
    vector<int> chosenIds;
    chosenIds.reserve(ins.m);
    for (int j = 1; j <= ins.m; ++j) if (bestSol.chosen[j]) chosenIds.push_back(j);
    cout << chosenIds.size() << "\n";
    for (size_t i = 0; i < chosenIds.size(); ++i) {
        if (i) cout << ' ';
        cout << chosenIds[i];
    }
    cout << "\n";
    return 0;
}