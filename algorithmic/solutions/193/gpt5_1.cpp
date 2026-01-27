#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int u, v; // variable indices 1..n
    bool negU, negV; // true if literal is negated
};

struct Occur {
    int cid; // clause id
    int side; // 0 for u, 1 for v
};

struct Node {
    int gain;
    int ver;
    int var;
    bool operator<(const Node& other) const {
        if (gain != other.gain) return gain < other.gain; // max-heap by gain
        return var < other.var;
    }
};

static inline int contrib(int satCount, bool litTrue) {
    if (satCount == 0) return 1;
    if (satCount == 1) return litTrue ? -1 : 0;
    return 0; // satCount == 2
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<Occur>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clauses[i].u = abs(a);
        clauses[i].v = abs(b);
        clauses[i].negU = (a < 0);
        clauses[i].negV = (b < 0);
        if (a > 0) posCnt[clauses[i].u]++; else negCnt[clauses[i].u]++;
        if (b > 0) posCnt[clauses[i].v]++; else negCnt[clauses[i].v]++;
        occ[clauses[i].u].push_back({i, 0});
        occ[clauses[i].v].push_back({i, 1});
    }

    // Trivial case m == 0: output any assignment
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // RNG
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Best global assignment
    vector<char> bestAssign(n + 1, 0);
    int bestS = -1;

    // Flip budget
    long long flipBudget = min(500000LL, 20LL * m + 10000LL);
    long long flipsUsed = 0;

    // Per-try structures
    vector<char> assign(n + 1, 0);
    vector<int> varGain(n + 1, 0);
    vector<int> version(n + 1, 0);
    vector<char> clauseSat(m, 0);
    vector<int> unsatPos(m, -1);
    vector<int> unsatVec;
    priority_queue<Node> pq;

    auto pushAllToPQ = [&]() {
        while (!pq.empty()) pq.pop();
        for (int v = 1; v <= n; ++v) {
            pq.push({varGain[v], version[v], v});
        }
    };

    auto getTopValid = [&]() -> Node {
        while (!pq.empty()) {
            Node t = pq.top();
            if (t.ver == version[t.var] && t.gain == varGain[t.var]) return t;
            pq.pop();
        }
        // Refill if empty
        pushAllToPQ();
        if (!pq.empty()) {
            Node t = pq.top();
            if (t.ver == version[t.var] && t.gain == varGain[t.var]) return t;
        }
        return Node{INT_MIN, -1, -1};
    };

    auto removeUnsat = [&](int cid) {
        int pos = unsatPos[cid];
        if (pos == -1) return;
        int lastCid = unsatVec.back();
        unsatVec[pos] = lastCid;
        unsatPos[lastCid] = pos;
        unsatVec.pop_back();
        unsatPos[cid] = -1;
    };

    auto addUnsat = [&](int cid) {
        if (unsatPos[cid] != -1) return;
        unsatPos[cid] = (int)unsatVec.size();
        unsatVec.push_back(cid);
    };

    auto initializeAssignment = [&](bool randomize) {
        // Majority assignment with small noise
        for (int v = 1; v <= n; ++v) {
            int choose1 = (posCnt[v] >= negCnt[v]) ? 1 : 0;
            if (randomize) {
                // small noise
                uniform_int_distribution<int> dist(0, 99);
                if (dist(rng) < 10) choose1 ^= 1;
            }
            assign[v] = (char)choose1;
            version[v] = 0;
            varGain[v] = 0;
        }
        // Compute clause satisfaction, gains
        unsatVec.clear();
        fill(unsatPos.begin(), unsatPos.end(), -1);
        int S = 0;
        for (int i = 0; i < m; ++i) {
            const Clause &C = clauses[i];
            bool tU = (assign[C.u] ^ C.negU);
            bool tV = (assign[C.v] ^ C.negV);
            int cnt = (tU ? 1 : 0) + (tV ? 1 : 0);
            clauseSat[i] = (char)cnt;
            if (cnt == 0) {
                varGain[C.u] += 1;
                varGain[C.v] += 1;
                addUnsat(i);
            } else if (cnt == 1) {
                if (tU) varGain[C.u] -= 1;
                if (tV) varGain[C.v] -= 1;
                S++;
            } else {
                S++;
            }
        }
        // Build PQ
        pushAllToPQ();
        return S;
    };

    auto flipVar = [&](int x, int &S) {
        char oldAx = assign[x];
        assign[x] ^= 1;
        version[x]++;

        static vector<int> touched;
        static vector<char> touchedMark;
        if (touchedMark.empty()) touchedMark.assign(n + 1, 0);
        touched.clear();
        touched.push_back(x);
        touchedMark[x] = 1;

        for (const auto &oc : occ[x]) {
            int cid = oc.cid;
            Clause &C = clauses[cid];
            int oldSat = clauseSat[cid];

            bool newTU = (assign[C.u] ^ C.negU);
            bool newTV = (assign[C.v] ^ C.negV);
            int newSat = (newTU ? 1 : 0) + (newTV ? 1 : 0);

            if (oldSat == 0 && newSat > 0) {
                S++;
                removeUnsat(cid);
            } else if (oldSat > 0 && newSat == 0) {
                S--;
                addUnsat(cid);
            }
            clauseSat[cid] = (char)newSat;

            int y;
            bool oldTruthX, newTruthX, oldTruthY, newTruthY;
            if (oc.side == 0) {
                // x corresponds to u
                oldTruthX = ((oldAx) ^ C.negU); // oldAx because before flip
                newTruthX = newTU;
                y = C.v;
                oldTruthY = (assign[C.v] ^ C.negV); // unchanged by flip
                newTruthY = oldTruthY;
            } else {
                // x corresponds to v
                oldTruthX = ((oldAx) ^ C.negV);
                newTruthX = newTV;
                y = C.u;
                oldTruthY = (assign[C.u] ^ C.negU);
                newTruthY = oldTruthY;
            }

            int oldCX = contrib(oldSat, oldTruthX);
            int newCX = contrib(newSat, newTruthX);
            varGain[x] += (newCX - oldCX);

            int oldCY = contrib(oldSat, oldTruthY);
            int newCY = contrib(newSat, newTruthY);
            varGain[y] += (newCY - oldCY);

            if (!touchedMark[y]) {
                touchedMark[y] = 1;
                touched.push_back(y);
            }
        }

        // push updated nodes
        pq.push({varGain[x], version[x], x});
        for (int v : touched) {
            if (v == x) continue;
            pq.push({varGain[v], version[v], v});
            touchedMark[v] = 0;
        }
        touchedMark[x] = 0;
    };

    // Main loop with multiple restarts
    while (flipsUsed < flipBudget && bestS < m) {
        bool randomize = (flipsUsed > 0);
        int S = initializeAssignment(randomize);

        if (S > bestS) {
            bestS = S;
            bestAssign = assign;
            if (bestS == m) break;
        }

        long long perTryLimit = min(20000LL, flipBudget - flipsUsed);
        double walkProb = 0.15;

        for (long long it = 0; it < perTryLimit && flipsUsed < flipBudget && bestS < m; ++it) {
            flipsUsed++;
            // Choose variable to flip
            int chosenVar = -1;

            // With probability walkProb, do random walk on unsatisfied clause (if any)
            bool doWalk = false;
            if (!unsatVec.empty()) {
                uniform_real_distribution<double> prob(0.0, 1.0);
                if (prob(rng) < walkProb) doWalk = true;
            }

            if (doWalk) {
                // Pick a random unsatisfied clause
                uniform_int_distribution<int> dist(0, (int)unsatVec.size() - 1);
                int cid = unsatVec[dist(rng)];
                const Clause &C = clauses[cid];
                int u = C.u, v = C.v;
                int gu = varGain[u], gv = varGain[v];
                if (gu > gv) chosenVar = u;
                else if (gv > gu) chosenVar = v;
                else {
                    // tie break random
                    uniform_int_distribution<int> b01(0, 1);
                    chosenVar = b01(rng) ? u : v;
                }
            } else {
                Node top = getTopValid();
                if (top.var != -1 && top.gain > 0) {
                    chosenVar = top.var;
                } else {
                    // No positive gain; if there are unsatisfied clauses, pick from one
                    if (!unsatVec.empty()) {
                        uniform_int_distribution<int> dist(0, (int)unsatVec.size() - 1);
                        int cid = unsatVec[dist(rng)];
                        const Clause &C = clauses[cid];
                        int u = C.u, v = C.v;
                        int gu = varGain[u], gv = varGain[v];
                        if (gu > gv) chosenVar = u;
                        else if (gv > gu) chosenVar = v;
                        else {
                            uniform_int_distribution<int> b01(0, 1);
                            chosenVar = b01(rng) ? u : v;
                        }
                    } else {
                        // Everything satisfied or no improvement possible
                        break;
                    }
                }
            }

            if (chosenVar == -1) break;

            flipVar(chosenVar, S);

            if (S > bestS) {
                bestS = S;
                bestAssign = assign;
                if (bestS == m) break;
            }
        }
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << '\n';
    return 0;
}