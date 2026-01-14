#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t s;
    RNG(uint64_t seed = 0) {
        if (seed == 0) {
            seed = chrono::high_resolution_clock::now().time_since_epoch().count();
            seed ^= (uint64_t)(uintptr_t)this;
        }
        s = seed;
    }
    inline uint64_t next() {
        uint64_t z = (s += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t next_u32() { return (uint32_t)next(); }
    inline uint64_t next_u64() { return next(); }
    inline size_t next_size_t() { return (size_t)next(); }
    inline uint64_t rand_range(uint64_t n) { return n ? next_u64() % n : 0; } // 0..n-1
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<array<int,3>> clauses(m);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
    }

    // Adjacency: for each variable v, list of (clause index, position 0..2)
    vector<vector<pair<int,int>>> occ(n + 1);
    for (int ci = 0; ci < m; ++ci) {
        for (int k = 0; k < 3; ++k) {
            int lit = clauses[ci][k];
            int v = abs(lit);
            if (v >= 1 && v <= n) {
                occ[v].push_back({ci, k});
            }
        }
    }

    RNG rng;

    vector<char> assign(n + 1, 0);
    vector<int> sat_count(m, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsatList; unsatList.reserve(m);

    auto literalTrue = [&](int lit)->bool {
        int v = abs(lit);
        bool val = assign[v];
        return (lit > 0) ? val : !val;
    };

    auto addUnsat = [&](int c){
        if (posInUnsat[c] == -1) {
            posInUnsat[c] = (int)unsatList.size();
            unsatList.push_back(c);
        }
    };
    auto removeUnsat = [&](int c){
        int pos = posInUnsat[c];
        if (pos != -1) {
            int last = unsatList.back();
            unsatList[pos] = last;
            posInUnsat[last] = pos;
            unsatList.pop_back();
            posInUnsat[c] = -1;
        }
    };

    auto init_random_assignment = [&](){
        for (int v = 1; v <= n; ++v) {
            assign[v] = (char)(rng.next_u64() & 1ULL);
        }
        unsatList.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int c = 0; c < m; ++c) {
            int sc = 0;
            sc += literalTrue(clauses[c][0]);
            sc += literalTrue(clauses[c][1]);
            sc += literalTrue(clauses[c][2]);
            sat_count[c] = sc;
            if (sc == 0) addUnsat(c);
        }
    };

    auto compute_break = [&](int v)->int {
        int br = 0;
        const auto &L = occ[v];
        bool val = assign[v];
        for (auto &pr : L) {
            int ci = pr.first;
            if (sat_count[ci] == 1) {
                int pos = pr.second;
                int lit = clauses[ci][pos];
                bool litTrue = (lit > 0) ? val : !val;
                if (litTrue) ++br;
            }
        }
        return br;
    };

    auto flip_var = [&](int v){
        bool oldVal = assign[v];
        assign[v] = (char)(!oldVal);
        const auto &L = occ[v];
        for (auto &pr : L) {
            int ci = pr.first;
            int oldsc = sat_count[ci];
            int pos = pr.second;
            int lit = clauses[ci][pos];
            bool wasTrue = (lit > 0) ? oldVal : !oldVal;
            int newsc = oldsc + (wasTrue ? -1 : 1);
            sat_count[ci] = newsc;
            if (oldsc == 0 && newsc > 0) {
                removeUnsat(ci);
            } else if (oldsc > 0 && newsc == 0) {
                addUnsat(ci);
            }
        }
    };

    vector<char> bestAssign(n + 1, 0);
    int bestUnsat = m; // number of unsatisfied clauses in best found
    double timeLimitSec = 0.9; // soft time limit
    auto t_start = chrono::high_resolution_clock::now();

    auto elapsedSec = [&](){
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - t_start).count();
    };

    if (m == 0) {
        // Any assignment
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    // Try multiple restarts
    const double p_random_walk = 0.5;
    int restart = 0;
    while (elapsedSec() < timeLimitSec) {
        ++restart;
        init_random_assignment();
        int currentUnsat = (int)unsatList.size();
        if (currentUnsat < bestUnsat) {
            bestUnsat = currentUnsat;
            bestAssign = assign;
            if (bestUnsat == 0) break;
        }

        // Steps per restart bound
        int stepLimit = max(10000, min(200000, 30 * m));
        for (int step = 0; step < stepLimit; ++step) {
            if (unsatList.empty()) {
                bestUnsat = 0;
                bestAssign = assign;
                break;
            }
            if ((step & 255) == 0 && elapsedSec() >= timeLimitSec) break;

            int cidx = unsatList[(size_t)rng.rand_range(unsatList.size())];

            int choiceVar;
            if ((rng.next_u32() & 1) || (p_random_walk > 0.0 && (rng.next_u32() % 1000) < (int)(p_random_walk * 1000))) {
                // Random walk: pick random literal in the clause
                int pos = (int)(rng.next_u32() % 3);
                choiceVar = abs(clauses[cidx][pos]);
            } else {
                // Greedy: pick variable in clause with minimum break count
                int bestV = abs(clauses[cidx][0]);
                int bestBr = compute_break(bestV);
                bool zeroFound = (bestBr == 0);
                for (int k = 1; k < 3; ++k) {
                    int v = abs(clauses[cidx][k]);
                    int br = compute_break(v);
                    if (br < bestBr || (br == bestBr && (rng.next_u32() & 1))) {
                        bestBr = br;
                        bestV = v;
                    }
                    if (br == 0) zeroFound = true;
                }
                // Favor zero break if exists
                if (!zeroFound && (rng.next_u32() & 1)) {
                    // occasional randomness to escape local minima
                    int pos = (int)(rng.next_u32() % 3);
                    bestV = abs(clauses[cidx][pos]);
                }
                choiceVar = bestV;
            }

            flip_var(choiceVar);

            currentUnsat = (int)unsatList.size();
            if (currentUnsat < bestUnsat) {
                bestUnsat = currentUnsat;
                bestAssign = assign;
                if (bestUnsat == 0) break;
            }
        }
        if (bestUnsat == 0) break;
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        cout << (bestAssign[i] ? 1 : 0) << (i == n ? '\n' : ' ');
    }
    return 0;
}