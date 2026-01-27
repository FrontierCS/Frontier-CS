#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];
    inline char getChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool read(T &out) {
        char c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        T sign = 1;
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        T x = 0;
        for (; c >= '0' && c <= '9'; c = getChar()) x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
};

struct Solution {
    vector<int> ids; // 0-based ids
    long long cost = (1LL << 62);
    bool feasible = false;
};

struct Solver {
    int n, m;
    vector<long long> cost;
    vector<vector<int>> sets;        // sets[s] = list of elements
    vector<vector<int>> cont;        // cont[e] = list of sets containing e
    vector< bitset<512> > sbit;      // bitset representation of sets
    mt19937_64 rng;

    Solver(int n_, int m_) : n(n_), m(m_), cost(m_), sets(m_), cont(n_), sbit(m_) {
        rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    void buildBitsets() {
        for (int s = 0; s < m; ++s) {
            bitset<512> b;
            for (int e : sets[s]) {
                b.set(e);
            }
            sbit[s] = b;
        }
    }

    // Greedy with optional GRASP parameter alpha (0 = pure greedy)
    Solution greedy(double alpha) {
        vector<char> covered(n, 0);
        vector<int> curUncov(m);
        for (int s = 0; s < m; ++s) curUncov[s] = (int)sets[s].size();
        vector<char> chosen(m, 0);
        vector<int> chosenList;
        long long sumCost = 0;
        int rem = n;

        // feasibility early check
        for (int e = 0; e < n; ++e) if (cont[e].empty()) {
            Solution sol;
            sol.ids.clear();
            sol.cost = (1LL << 62);
            sol.feasible = false;
            return sol;
        }

        while (rem > 0) {
            double minRat = 1e300, maxRat = -1.0;
            int minId = -1;

            // First pass: find min/max ratio among available sets
            for (int s = 0; s < m; ++s) {
                if (chosen[s]) continue;
                int cu = curUncov[s];
                if (cu <= 0) continue;
                double r = (double)cost[s] / (double)cu;
                if (r < minRat) {
                    minRat = r;
                    minId = s;
                }
                if (r > maxRat) maxRat = r;
            }
            if (minId == -1) {
                // No set can cover remaining elements -> infeasible
                Solution sol;
                sol.ids = chosenList;
                sol.cost = sumCost;
                sol.feasible = false;
                return sol;
            }

            int pick = minId;
            if (alpha > 1e-12 && maxRat >= minRat) {
                double threshold = minRat + alpha * (maxRat - minRat);
                vector<int> rcl;
                rcl.reserve(64);
                for (int s = 0; s < m; ++s) {
                    if (chosen[s]) continue;
                    int cu = curUncov[s];
                    if (cu <= 0) continue;
                    double r = (double)cost[s] / (double)cu;
                    if (r <= threshold + 1e-18) {
                        rcl.push_back(s);
                    }
                }
                if (!rcl.empty()) {
                    uniform_int_distribution<int> dist(0, (int)rcl.size() - 1);
                    pick = rcl[dist(rng)];
                }
            }

            // select pick
            chosen[pick] = 1;
            chosenList.push_back(pick);
            sumCost += cost[pick];

            // cover elements and update curUncov
            for (int e : sets[pick]) {
                if (!covered[e]) {
                    covered[e] = 1;
                    --rem;
                    for (int t : cont[e]) {
                        if (curUncov[t] > 0) curUncov[t]--;
                    }
                }
            }
        }

        Solution sol;
        sol.ids = chosenList;
        sol.cost = sumCost;
        sol.feasible = true;
        return sol;
    }

    // Remove redundant sets from a chosen solution
    void removeRedundant(vector<int> &chosenIds) {
        vector<char> inSol(m, 0);
        for (int s : chosenIds) inSol[s] = 1;
        vector<int> coverCount(n, 0);
        for (int s : chosenIds) {
            for (int e : sets[s]) coverCount[e]++;
        }
        // Sort by decreasing cost to remove expensive first
        vector<int> order = chosenIds;
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (cost[a] != cost[b]) return cost[a] > cost[b];
            return a < b;
        });
        for (int s : order) {
            if (!inSol[s]) continue;
            bool canRemove = true;
            for (int e : sets[s]) {
                if (coverCount[e] <= 1) { canRemove = false; break; }
            }
            if (canRemove) {
                inSol[s] = 0;
                for (int e : sets[s]) coverCount[e]--;
            }
        }
        chosenIds.clear();
        for (int s = 0; s < m; ++s) if (inSol[s]) chosenIds.push_back(s);
    }

    // One-swap improvement: replace one chosen set by a cheaper single set covering its critical elements
    void oneSwapImprove(vector<int> &chosenIds) {
        vector<char> chosen(m, 0);
        for (int s : chosenIds) chosen[s] = 1;

        vector<int> coverCount(n, 0);
        for (int s = 0; s < m; ++s) if (chosen[s]) {
            for (int e : sets[s]) coverCount[e]++;
        }

        auto rebuildChosenIds = [&]() {
            chosenIds.clear();
            for (int s = 0; s < m; ++s) if (chosen[s]) chosenIds.push_back(s);
        };

        // Build ones bitset
        bitset<512> ones;
        for (int e = 0; e < n; ++e) if (coverCount[e] == 1) ones.set(e);

        bool improved = true;
        while (improved) {
            improved = false;
            // Iterate over chosen sets, attempt to swap with a cheaper single set
            for (int s = 0; s < m; ++s) {
                if (!chosen[s]) continue;
                bitset<512> crit = sbit[s] & ones;
                if (crit.none()) continue;

                int bestT = -1;
                long long bestCost = LLONG_MAX;
                for (int t = 0; t < m; ++t) {
                    if (chosen[t]) continue;
                    if (cost[t] >= cost[s]) continue;
                    // Check if sbit[t] is a superset of crit: (crit & ~sbit[t]) == 0
                    bitset<512> tmp = crit & (~sbit[t]);
                    if (tmp.any()) continue;
                    if (cost[t] < bestCost) {
                        bestCost = cost[t];
                        bestT = t;
                    }
                }
                if (bestT != -1) {
                    // Perform swap s -> bestT
                    chosen[s] = 0;
                    chosen[bestT] = 1;

                    // Update coverCount and ones incrementally
                    for (int e : sets[bestT]) {
                        int old = coverCount[e];
                        int nw = old + 1;
                        coverCount[e] = nw;
                        if (old == 0) ones.set(e);
                        else if (old == 1) ones.reset(e);
                    }
                    for (int e : sets[s]) {
                        int old = coverCount[e];
                        int nw = old - 1;
                        coverCount[e] = nw;
                        if (old == 1) ones.reset(e);
                        else if (old == 2) ones.set(e);
                    }
                    improved = true;
                    break;
                }
            }
        }
        rebuildChosenIds();
    }

    long long computeCost(const vector<int> &ids) {
        long long s = 0;
        for (int x : ids) s += cost[x];
        return s;
    }

    bool checkFeasible(const vector<int> &ids) {
        vector<int> cover(n, 0);
        for (int s : ids) {
            for (int e : sets[s]) cover[e] = 1;
        }
        for (int e = 0; e < n; ++e) if (!cover[e]) return false;
        return true;
    }

    Solution solve() {
        buildBitsets();

        // Multi-start GRASP
        Solution best;
        best.feasible = false;
        best.cost = (1LL << 62);

        auto start = std::chrono::high_resolution_clock::now();
        double timeLimitSec = 1.5; // keep well under 10s
        int maxRuns = 60;

        // Run a deterministic greedy first
        {
            Solution sol = greedy(0.0);
            if (sol.feasible) {
                removeRedundant(sol.ids);
                oneSwapImprove(sol.ids);
                removeRedundant(sol.ids);
                sol.cost = computeCost(sol.ids);
                sol.feasible = checkFeasible(sol.ids);
                if (sol.feasible && sol.cost < best.cost) best = sol;
            }
        }

        uniform_real_distribution<double> distAlpha(0.0, 0.4);

        for (int iter = 0; iter < maxRuns; ++iter) {
            auto now = std::chrono::high_resolution_clock::now();
            double elapsed = std::chrono::duration<double>(now - start).count();
            if (elapsed > timeLimitSec) break;

            double alpha = distAlpha(rng);
            Solution sol = greedy(alpha);
            if (!sol.feasible) continue;

            removeRedundant(sol.ids);
            oneSwapImprove(sol.ids);
            removeRedundant(sol.ids);
            sol.cost = computeCost(sol.ids);
            sol.feasible = checkFeasible(sol.ids);
            if (sol.feasible && sol.cost < best.cost) best = sol;
        }

        if (!best.feasible) {
            // Fallback: empty solution (infeasible), though inputs should allow feasible solution
            best.ids.clear();
            best.cost = 0;
            best.feasible = false;
        }
        return best;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.read(n)) return 0;
    fs.read(m);
    Solver solver(n, m);
    for (int i = 0; i < m; ++i) {
        long long c;
        fs.read(c);
        solver.cost[i] = c;
    }
    for (int i = 0; i < n; ++i) {
        int k;
        fs.read(k);
        for (int j = 0; j < k; ++j) {
            int a;
            fs.read(a);
            --a; // 0-based
            if (a >= 0 && a < m) {
                solver.sets[a].push_back(i);
                solver.cont[i].push_back(a);
            }
        }
    }

    Solution best = solver.solve();

    // Output solution
    vector<int> ans = best.ids;
    sort(ans.begin(), ans.end());
    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); ++i) {
        if (i) cout << ' ';
        cout << (ans[i] + 1);
    }
    cout << "\n";
    return 0;
}