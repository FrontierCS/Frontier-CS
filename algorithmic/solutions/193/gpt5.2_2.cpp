#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b; // b==0 means unit clause (a)
};

struct Occ {
    int c;
    bool pos;
};

static inline int litId(int lit) {
    int v = abs(lit) - 1;
    return 2 * v + (lit > 0 ? 0 : 1);
}

static inline int litTrue(int lit, const vector<char>& val) {
    int v = abs(lit);
    return (lit > 0) ? (int)val[v] : (int)(val[v] ^ 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // Build implication graph for satisfiable 2-SAT check
    int N = 2 * n;
    vector<vector<int>> g(N), rg(N);
    g.reserve(N);
    rg.reserve(N);

    vector<pair<int,int>> inputClauses;
    inputClauses.reserve(m);

    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        inputClauses.push_back({a, b});

        int ia = litId(a), ib = litId(b);
        int na = ia ^ 1, nb = ib ^ 1;

        g[na].push_back(ib);
        rg[ib].push_back(na);

        g[nb].push_back(ia);
        rg[ia].push_back(nb);
    }

    // Kosaraju SCC
    vector<char> vis(N, 0);
    vector<int> order;
    order.reserve(N);

    for (int s = 0; s < N; s++) {
        if (vis[s]) continue;
        vector<pair<int,int>> st;
        st.reserve(64);
        st.push_back({s, 0});
        vis[s] = 1;
        while (!st.empty()) {
            auto &top = st.back();
            int v = top.first;
            int &it = top.second;
            if (it < (int)g[v].size()) {
                int to = g[v][it++];
                if (!vis[to]) {
                    vis[to] = 1;
                    st.push_back({to, 0});
                }
            } else {
                order.push_back(v);
                st.pop_back();
            }
        }
    }

    vector<int> comp(N, -1);
    int cid = 0;
    for (int idx = N - 1; idx >= 0; idx--) {
        int s = order[idx];
        if (comp[s] != -1) continue;
        vector<int> st;
        st.reserve(64);
        st.push_back(s);
        comp[s] = cid;
        while (!st.empty()) {
            int v = st.back();
            st.pop_back();
            for (int to : rg[v]) {
                if (comp[to] == -1) {
                    comp[to] = cid;
                    st.push_back(to);
                }
            }
        }
        cid++;
    }

    bool sat = true;
    vector<int> assign(n + 1, 0);
    for (int i = 0; i < n; i++) {
        if (comp[2 * i] == comp[2 * i + 1]) {
            sat = false;
            break;
        }
        assign[i + 1] = (comp[2 * i] > comp[2 * i + 1]) ? 1 : 0;
    }

    if (sat) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << assign[i];
        }
        cout << '\n';
        return 0;
    }

    // Max-2-SAT heuristic (WalkSAT-like) on simplified clauses
    int tautCount = 0;
    vector<Clause> clauses;
    clauses.reserve(m);

    for (auto [a, b] : inputClauses) {
        if (abs(a) == abs(b)) {
            if (a == -b) { // tautology
                tautCount++;
                continue;
            } else { // unit clause
                clauses.push_back({a, 0});
            }
        } else {
            clauses.push_back({a, b});
        }
    }

    int mEff = (int)clauses.size();
    if (mEff == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<vector<Occ>> occ(n + 1);
    for (int i = 0; i < mEff; i++) {
        int a = clauses[i].a;
        occ[abs(a)].push_back({i, a > 0});
        if (clauses[i].b != 0) {
            int b = clauses[i].b;
            occ[abs(b)].push_back({i, b > 0});
        }
    }

    vector<uint8_t> satCount(mEff, 0);
    vector<int> posInUnsat(mEff, -1);
    vector<int> unsatList;
    unsatList.reserve(mEff);

    auto addUnsat = [&](int c) {
        if (posInUnsat[c] != -1) return;
        posInUnsat[c] = (int)unsatList.size();
        unsatList.push_back(c);
    };

    auto removeUnsat = [&](int c) {
        int p = posInUnsat[c];
        if (p == -1) return;
        int last = unsatList.back();
        unsatList[p] = last;
        posInUnsat[last] = p;
        unsatList.pop_back();
        posInUnsat[c] = -1;
    };

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto rnd01 = [&]() -> double {
        // 53-bit precision [0,1)
        return (rng() >> 11) * (1.0 / 9007199254740992.0);
    };
    auto randint = [&](int k) -> int {
        return (int)(rng() % (uint64_t)k);
    };

    vector<char> val(n + 1, 0), bestVal(n + 1, 0);
    int bestUnsat = mEff;

    auto initRandom = [&]() {
        for (int i = 1; i <= n; i++) val[i] = (char)(rng() & 1ULL);
        unsatList.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);

        for (int c = 0; c < mEff; c++) {
            int sc = litTrue(clauses[c].a, val);
            if (clauses[c].b != 0) sc += litTrue(clauses[c].b, val);
            satCount[c] = (uint8_t)sc;
            if (sc == 0) addUnsat(c);
        }
    };

    auto computeDelta = [&](int v) -> int {
        char oldVal = val[v];
        int delta = 0;
        for (const auto &o : occ[v]) {
            bool before = o.pos ? (oldVal != 0) : (oldVal == 0);
            uint8_t sc = satCount[o.c];
            if (before) {
                if (sc == 1) delta--; // clause would become unsatisfied
            } else {
                if (sc == 0) delta++; // clause would become satisfied
            }
        }
        return delta;
    };

    auto flipVar = [&](int v) {
        char oldVal = val[v];
        char newVal = oldVal ^ 1;
        for (const auto &o : occ[v]) {
            bool before = o.pos ? (oldVal != 0) : (oldVal == 0);
            int c = o.c;
            uint8_t oldSc = satCount[c];
            uint8_t newSc = (uint8_t)(oldSc + (before ? -1 : +1));
            satCount[c] = newSc;

            if (oldSc == 0 && newSc == 1) removeUnsat(c);
            else if (oldSc == 1 && newSc == 0) addUnsat(c);
        }
        val[v] = newVal;
    };

    // Heuristic loop
    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(950); // conservative

    const double noise = 0.35;
    const int stagnationLimit = 20000;

    while (chrono::steady_clock::now() < deadline) {
        initRandom();

        int bestUnsatRun = (int)unsatList.size();
        int lastImprove = 0;

        if ((int)unsatList.size() < bestUnsat) {
            bestUnsat = (int)unsatList.size();
            bestVal = val;
            if (bestUnsat == 0) break;
        }

        int steps = 0;
        while (chrono::steady_clock::now() < deadline) {
            if (unsatList.empty()) {
                bestUnsat = 0;
                bestVal = val;
                break;
            }

            if ((int)unsatList.size() < bestUnsat) {
                bestUnsat = (int)unsatList.size();
                bestVal = val;
                if (bestUnsat == 0) break;
            }
            if ((int)unsatList.size() < bestUnsatRun) {
                bestUnsatRun = (int)unsatList.size();
                lastImprove = steps;
            }
            if (steps - lastImprove > stagnationLimit) break;

            int c = unsatList[randint((int)unsatList.size())];
            int a = clauses[c].a;
            int b = clauses[c].b;

            int chosen = abs(a);
            if (b != 0) {
                int v1 = abs(a), v2 = abs(b);
                if (rnd01() < noise) {
                    chosen = (randint(2) == 0) ? v1 : v2;
                } else {
                    int d1 = computeDelta(v1);
                    int d2 = computeDelta(v2);
                    if (d1 > d2) chosen = v1;
                    else if (d2 > d1) chosen = v2;
                    else chosen = (randint(2) == 0) ? v1 : v2;
                }
            }

            flipVar(chosen);
            steps++;

            if ((steps & 2047) == 0 && chrono::steady_clock::now() >= deadline) break;
        }

        if (bestUnsat == 0) break;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}