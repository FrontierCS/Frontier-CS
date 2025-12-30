#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::high_resolution_clock::time_point start;
    Timer() { reset(); }
    void reset() { start = chrono::high_resolution_clock::now(); }
    double elapsed() const {
        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> diff = now - start;
        return diff.count();
    }
};

struct Node {
    double ratio;
    int ver;
    int id;
    bool operator<(const Node& other) const {
        if (ratio != other.ratio) return ratio > other.ratio; // min-heap via > 
        return id > other.id;
    }
};

static const double GLOBAL_TIME_LIMIT = 9.5; // seconds (slightly below 10s as buffer)

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        cout << 0 << "\n\n";
        return 0;
    }
    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; i++) cin >> cost[i];

    vector<vector<int>> setsOfElement(n + 1);
    vector<vector<int>> elemsOfSet(m + 1);
    for (int i = 1; i <= n; i++) {
        int k; cin >> k;
        setsOfElement[i].reserve(k);
        for (int j = 0; j < k; j++) {
            int a; cin >> a;
            if (a >= 1 && a <= m) {
                setsOfElement[i].push_back(a);
                elemsOfSet[a].push_back(i);
            }
        }
    }

    Timer timer;

    // Helper lambdas
    auto compute_counts_cost = [&](const vector<char>& chosen, vector<int>& counts) -> long long {
        fill(counts.begin(), counts.end(), 0);
        long long tot = 0;
        for (int s = 1; s <= m; s++) if (chosen[s]) {
            tot += cost[s];
            for (int e : elemsOfSet[s]) counts[e]++;
        }
        return tot;
    };

    auto reduce_redundant = [&](vector<char>& chosen, vector<int>& counts, long long& totCost) {
        vector<int> order;
        order.reserve(m);
        for (int s = 1; s <= m; s++) if (chosen[s]) order.push_back(s);
        sort(order.begin(), order.end(), [&](int a, int b){
            if (cost[a] != cost[b]) return cost[a] > cost[b];
            return elemsOfSet[a].size() > elemsOfSet[b].size();
        });
        for (int s : order) if (chosen[s]) {
            bool can = true;
            for (int e : elemsOfSet[s]) {
                if (counts[e] <= 1) { can = false; break; }
            }
            if (can) {
                chosen[s] = 0;
                totCost -= cost[s];
                for (int e : elemsOfSet[s]) counts[e]--;
            }
        }
    };

    auto one_swap_improve = [&](vector<char>& chosen, vector<int>& counts, long long& totCost, mt19937& rng, double timeBudgetLeft) {
        // time guard inside
        vector<int> selected;
        selected.reserve(m);
        for (int s = 1; s <= m; s++) if (chosen[s]) selected.push_back(s);
        if (selected.empty()) return;
        shuffle(selected.begin(), selected.end(), rng);

        vector<int> mark(m + 1, 0);
        vector<int> touched; touched.reserve(m);

        Timer tloc;
        for (int s : selected) {
            if (tloc.elapsed() > timeBudgetLeft) break;
            if (!chosen[s]) continue;

            // collect unique elements for s
            vector<int> uniq;
            uniq.reserve(elemsOfSet[s].size());
            for (int e : elemsOfSet[s]) if (counts[e] == 1) uniq.push_back(e);

            if (uniq.empty()) {
                // redundant, safe to remove
                bool can = true;
                for (int e : elemsOfSet[s]) if (counts[e] <= 1) { can = false; break; }
                if (can) {
                    chosen[s] = 0;
                    totCost -= cost[s];
                    for (int e : elemsOfSet[s]) counts[e]--;
                }
                continue;
            }

            // find candidate set t that covers all uniq
            touched.clear();
            for (int e : uniq) {
                for (int tset : setsOfElement[e]) {
                    if (mark[tset] == 0) touched.push_back(tset);
                    mark[tset]++;
                }
            }
            int need = (int)uniq.size();
            long long bestC = LLONG_MAX;
            int bestT = -1;
            for (int tset : touched) {
                if (mark[tset] == need && !chosen[tset]) {
                    long long c = cost[tset];
                    if (c < bestC) {
                        bestC = c;
                        bestT = tset;
                    }
                }
            }
            for (int tset : touched) mark[tset] = 0;

            if (bestT != -1 && bestC < cost[s]) {
                // perform swap s -> bestT
                chosen[s] = 0;
                for (int e : elemsOfSet[s]) counts[e]--;
                chosen[bestT] = 1;
                for (int e : elemsOfSet[bestT]) counts[e]++;
                totCost += bestC - cost[s];
            }
        }
    };

    auto build_selected_list = [&](const vector<char>& chosen) {
        vector<int> res;
        res.reserve(m);
        for (int s = 1; s <= m; s++) if (chosen[s]) res.push_back(s);
        return res;
    };

    // Baseline: pick cheapest set per element
    vector<char> bestChosen(m + 1, 0);
    {
        for (int e = 1; e <= n; e++) {
            if (setsOfElement[e].empty()) continue;
            int bestSet = -1;
            long long bestC = LLONG_MAX;
            for (int s : setsOfElement[e]) {
                if (cost[s] < bestC) {
                    bestC = cost[s];
                    bestSet = s;
                }
            }
            if (bestSet != -1) bestChosen[bestSet] = 1;
        }
    }
    vector<int> counts(n + 1, 0);
    long long bestCost = compute_counts_cost(bestChosen, counts);
    reduce_redundant(bestChosen, counts, bestCost);
    {
        mt19937 rng_init((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ 0x9e3779b97f4a7c15ULL);
        double timeLeft = GLOBAL_TIME_LIMIT - timer.elapsed();
        if (timeLeft > 0.2)
            one_swap_improve(bestChosen, counts, bestCost, rng_init, min(1.0, timeLeft * 0.5));
        reduce_redundant(bestChosen, counts, bestCost);
    }
    vector<int> bestList = build_selected_list(bestChosen);

    // Prepare for greedy restarts
    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uintptr_t)&n);

    vector<int> deg(n + 1, 0);
    for (int i = 1; i <= n; i++) deg[i] = (int)setsOfElement[i].size();

    // Greedy restarts
    while (timer.elapsed() < GLOBAL_TIME_LIMIT) {
        double timeRemaining = GLOBAL_TIME_LIMIT - timer.elapsed();
        if (timeRemaining < 0.1) break;

        // random parameters
        uniform_real_distribution<double> distRho(0.05, 0.25);
        uniform_real_distribution<double> distU(-1.0, 1.0);
        uniform_real_distribution<double> distGamma(0.8, 1.2);
        double rho = distRho(rng);
        double gamma = distGamma(rng);

        vector<double> wcost(m + 1);
        for (int s = 1; s <= m; s++) {
            double noise = 1.0 + rho * distU(rng);
            if (noise < 0.05) noise = 0.05;
            wcost[s] = cost[s] * noise;
        }
        vector<double> eWeight(n + 1, 0.0);
        for (int e = 1; e <= n; e++) {
            if (deg[e] > 0) eWeight[e] = 1.0 / pow((double)deg[e], gamma);
            else eWeight[e] = 0.0;
        }

        // Greedy using priority queue
        vector<char> chosen(m + 1, 0);
        vector<double> sumW(m + 1, 0.0);
        vector<int> ver(m + 1, 0);
        vector<int> covered(n + 1, 0);

        priority_queue<Node> pq;
        for (int s = 1; s <= m; s++) {
            double sw = 0.0;
            if (!elemsOfSet[s].empty()) {
                for (int e : elemsOfSet[s]) sw += eWeight[e];
            }
            sumW[s] = sw;
            if (sw > 1e-18) {
                pq.push(Node{ wcost[s] / sw, 0, s });
            }
        }
        int uncovered = 0;
        for (int e = 1; e <= n; e++) {
            if (deg[e] > 0) uncovered++;
        }

        while (uncovered > 0 && !pq.empty()) {
            Node cur = pq.top(); pq.pop();
            int s = cur.id;
            if (cur.ver != ver[s]) continue;
            if (chosen[s]) continue;
            if (sumW[s] <= 1e-18) continue;

            chosen[s] = 1;
            for (int e : elemsOfSet[s]) {
                if (deg[e] == 0) continue; // impossible element, ignore
                if (covered[e] == 0) {
                    covered[e] = 1;
                    uncovered--;
                    for (int tset : setsOfElement[e]) {
                        if (!chosen[tset]) {
                            double nw = sumW[tset] - eWeight[e];
                            if (nw < 0) nw = 0;
                            if (fabs(nw - sumW[tset]) > 0) {
                                sumW[tset] = nw;
                                ver[tset]++;
                                if (nw > 1e-18) {
                                    pq.push(Node{ wcost[tset] / nw, ver[tset], tset });
                                }
                            }
                        }
                    }
                }
            }
        }

        // Fallback to cover any still uncovered feasible elements
        if (uncovered > 0) {
            for (int e = 1; e <= n; e++) {
                if (deg[e] == 0) continue; // impossible
                if (covered[e] == 0) {
                    int bestSet = -1;
                    long long bestC = LLONG_MAX;
                    for (int s : setsOfElement[e]) {
                        if (cost[s] < bestC) { bestC = cost[s]; bestSet = s; }
                    }
                    if (bestSet != -1 && !chosen[bestSet]) {
                        chosen[bestSet] = 1;
                        for (int ee : elemsOfSet[bestSet]) {
                            if (deg[ee] == 0) continue;
                            if (covered[ee] == 0) {
                                covered[ee] = 1;
                                uncovered--;
                            }
                        }
                    }
                }
            }
        }

        // Evaluate and improve
        vector<int> countsR(n + 1, 0);
        long long costR = compute_counts_cost(chosen, countsR);
        reduce_redundant(chosen, countsR, costR);

        double timeLeft = GLOBAL_TIME_LIMIT - timer.elapsed();
        if (timeLeft > 0.2) {
            one_swap_improve(chosen, countsR, costR, rng, min(1.0, timeLeft * 0.5));
            reduce_redundant(chosen, countsR, costR);
        }

        if (costR < bestCost) {
            bestCost = costR;
            bestChosen = chosen;
            bestList = build_selected_list(bestChosen);
        }

        // early break if no time
        if (timer.elapsed() > GLOBAL_TIME_LIMIT) break;
    }

    // Output best found solution
    cout << bestList.size() << "\n";
    for (size_t i = 0; i < bestList.size(); i++) {
        if (i) cout << " ";
        cout << bestList[i];
    }
    cout << "\n";
    return 0;
}