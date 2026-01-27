#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int lit[3];
};

static inline bool clauseSatFlip(const Clause& cl, const vector<uint8_t>& asg, int flipVar) {
    for (int k = 0; k < 3; k++) {
        int lit = cl.lit[k];
        int v = lit > 0 ? lit : -lit;
        uint8_t val = asg[v];
        if (v == flipVar) val ^= 1;
        bool lval = (lit > 0) ? (val != 0) : (val == 0);
        if (lval) return true;
    }
    return false;
}

static inline bool clauseSat(const Clause& cl, const vector<uint8_t>& asg) {
    for (int k = 0; k < 3; k++) {
        int lit = cl.lit[k];
        int v = lit > 0 ? lit : -lit;
        uint8_t val = asg[v];
        bool lval = (lit > 0) ? (val != 0) : (val == 0);
        if (lval) return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<Clause> clauses(m);
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i].lit[0] = a;
        clauses[i].lit[1] = b;
        clauses[i].lit[2] = c;
        adj[abs(a)].push_back(i);
        adj[abs(b)].push_back(i);
        adj[abs(c)].push_back(i);
    }

    vector<uint8_t> bestAsg(n + 1, 0);
    int bestS = -1;

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85;

    vector<uint8_t> asg(n + 1);
    vector<uint8_t> sat(m);

    auto initRandom = [&]() {
        for (int i = 1; i <= n; i++) asg[i] = (uint8_t)(rng() & 1ULL);
        int S = 0;
        for (int i = 0; i < m; i++) {
            sat[i] = (uint8_t)clauseSat(clauses[i], asg);
            S += sat[i];
        }
        return S;
    };

    auto flipVar = [&](int v, int &S) {
        for (int idx : adj[v]) {
            uint8_t oldSat = sat[idx];
            uint8_t newSat = (uint8_t)clauseSatFlip(clauses[idx], asg, v);
            if (oldSat != newSat) {
                sat[idx] = newSat;
                S += (newSat ? 1 : -1);
            }
        }
        asg[v] ^= 1;
    };

    auto deltaIfFlip = [&](int v) {
        int delta = 0;
        for (int idx : adj[v]) {
            uint8_t oldSat = sat[idx];
            uint8_t newSat = (uint8_t)clauseSatFlip(clauses[idx], asg, v);
            if (oldSat != newSat) delta += (newSat ? 1 : -1);
        }
        return delta;
    };

    int restarts = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed >= TIME_LIMIT) break;

        int S = initRandom();
        if (S > bestS) {
            bestS = S;
            bestAsg = asg;
            if (bestS == m) break;
        }

        int stepsWithoutBest = 0;
        int maxSteps = 20000 + 2000 * n;

        for (int step = 0; step < maxSteps; step++) {
            now = chrono::steady_clock::now();
            elapsed = chrono::duration<double>(now - start).count();
            if (elapsed >= TIME_LIMIT) break;
            if (S == m) break;

            int ci = (int)(rng() % (uint64_t)m);
            for (int tries = 0; tries < 10 && sat[ci]; tries++) ci = (int)(rng() % (uint64_t)m);
            if (sat[ci]) {
                for (int i = 0; i < m; i++) {
                    if (!sat[i]) { ci = i; break; }
                }
            }
            const Clause& cl = clauses[ci];

            int vars[3] = { abs(cl.lit[0]), abs(cl.lit[1]), abs(cl.lit[2]) };

            int vpick;
            if ((rng() % 10ULL) < 2ULL) {
                vpick = vars[(int)(rng() % 3ULL)];
            } else {
                int bestDelta = -1e9;
                vpick = vars[0];
                for (int k = 0; k < 3; k++) {
                    int v = vars[k];
                    int d = deltaIfFlip(v);
                    if (d > bestDelta) {
                        bestDelta = d;
                        vpick = v;
                    } else if (d == bestDelta && (rng() & 1ULL)) {
                        vpick = v;
                    }
                }
            }

            int oldS = S;
            flipVar(vpick, S);

            if (S > bestS) {
                bestS = S;
                bestAsg = asg;
                stepsWithoutBest = 0;
                if (bestS == m) break;
            } else {
                stepsWithoutBest++;
            }

            if (stepsWithoutBest > 4000 && S < oldS) {
                // mild diversification: random flip
                int rv = (int)(rng() % (uint64_t)n) + 1;
                flipVar(rv, S);
                stepsWithoutBest = 0;
            }
        }

        restarts++;
        if (bestS == m) break;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (int)bestAsg[i];
    }
    cout << "\n";
    return 0;
}