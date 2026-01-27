#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v1, v2;
    unsigned char s1, s2; // 0 = false literal (negated), 1 = true literal (positive)
    unsigned char type;   // 0 = normal (v1 != v2), 1 = tautology (always true), 2 = unit (v1 == v2 and s1 == s2)
};

struct Occ {
    int ci;              // clause index
    unsigned char isFirst; // 1 if this occurrence refers to first literal, 0 if second
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<Clause> clauses(m);
    vector<vector<Occ>> occ(n + 1);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        int v1 = abs(a), v2 = abs(b);
        unsigned char s1 = (a > 0) ? 1 : 0;
        unsigned char s2 = (b > 0) ? 1 : 0;
        unsigned char type = 0;
        if (v1 == v2) {
            if (s1 != s2) type = 1; // tautology
            else type = 2;          // unit
        }
        clauses[i] = {v1, v2, s1, s2, type};
        if (type == 0) {
            occ[v1].push_back({i, 1});
            occ[v2].push_back({i, 0});
        } else if (type == 2) {
            occ[v1].push_back({i, 1});
        }
    }

    // Random generator
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto randBool = [&](void) -> unsigned char {
        return (unsigned char)(rng() & 1u);
    };
    auto randIdx = [&](int lim) -> int {
        std::uniform_int_distribution<int> dist(0, lim - 1);
        return dist(rng);
    };
    auto randProb = [&](void) -> double {
        return std::generate_canonical<double, 10>(rng);
    };

    vector<unsigned char> assign(n + 1);
    vector<unsigned char> bestAssign(n + 1);
    vector<int> breakC(n + 1), makeC(n + 1);
    vector<unsigned char> isSat(m);
    vector<int> posInUnsat(m, -1);
    vector<int> unsatList;
    int satisfiedCount = 0;
    int bestSatisfied = -1;

    auto clearState = [&]() {
        fill(breakC.begin(), breakC.end(), 0);
        fill(makeC.begin(), makeC.end(), 0);
        fill(isSat.begin(), isSat.end(), 0);
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        unsatList.clear();
        satisfiedCount = 0;
    };

    auto addUnsat = [&](int ci) {
        if (posInUnsat[ci] == -1) {
            posInUnsat[ci] = (int)unsatList.size();
            unsatList.push_back(ci);
        }
    };
    auto removeUnsat = [&](int ci) {
        int pos = posInUnsat[ci];
        if (pos != -1) {
            int last = unsatList.back();
            unsatList[pos] = last;
            posInUnsat[last] = pos;
            unsatList.pop_back();
            posInUnsat[ci] = -1;
        }
    };

    auto initializeFromAssignment = [&]() {
        clearState();
        for (int i = 0; i < m; ++i) {
            const Clause &c = clauses[i];
            if (c.type == 1) {
                // tautology: always satisfied
                isSat[i] = 1;
                satisfiedCount++;
                continue;
            } else if (c.type == 2) {
                // unit clause
                bool t = (assign[c.v1] == c.s1);
                if (t) {
                    isSat[i] = 1;
                    satisfiedCount++;
                    breakC[c.v1]++;
                } else {
                    isSat[i] = 0;
                    addUnsat(i);
                    makeC[c.v1]++;
                }
            } else {
                // normal clause
                bool t1 = (assign[c.v1] == c.s1);
                bool t2 = (assign[c.v2] == c.s2);
                if (t1 || t2) {
                    isSat[i] = 1;
                    satisfiedCount++;
                    if (t1 && !t2) breakC[c.v1]++;
                    else if (!t1 && t2) breakC[c.v2]++;
                } else {
                    isSat[i] = 0;
                    addUnsat(i);
                    makeC[c.v1]++;
                    makeC[c.v2]++;
                }
            }
        }
    };

    auto flipVar = [&](int x) {
        unsigned char oldVal = assign[x];
        for (const Occ &o : occ[x]) {
            int ci = o.ci;
            Clause &c = clauses[ci];
            if (c.type == 2) {
                // unit clause on x
                unsigned char sX = c.s1; // same both
                bool preSat = (oldVal == sX);
                if (preSat) {
                    // becomes unsatisfied
                    breakC[x]--;
                    makeC[x]++;
                    isSat[ci] = 0;
                    addUnsat(ci);
                    satisfiedCount--;
                } else {
                    // becomes satisfied
                    makeC[x]--;
                    breakC[x]++;
                    isSat[ci] = 1;
                    removeUnsat(ci);
                    satisfiedCount++;
                }
            } else {
                // normal clause (v1 != v2)
                int y = o.isFirst ? c.v2 : c.v1;
                unsigned char sX = o.isFirst ? c.s1 : c.s2;
                unsigned char sY = o.isFirst ? c.s2 : c.s1;
                bool xt = (oldVal == sX);
                bool yt = (assign[y] == sY);
                if (!xt && !yt) {
                    // pre unsatisfied -> post satisfied by x
                    makeC[x]--;
                    makeC[y]--;
                    breakC[x]++;
                    isSat[ci] = 1;
                    removeUnsat(ci);
                    satisfiedCount++;
                } else if (xt && !yt) {
                    // pre satisfied only by x -> post unsatisfied
                    breakC[x]--;
                    makeC[x]++;
                    makeC[y]++;
                    isSat[ci] = 0;
                    addUnsat(ci);
                    satisfiedCount--;
                } else if (!xt && yt) {
                    // pre satisfied only by y -> post both true
                    breakC[y]--;
                    // isSat remains true, satisfiedCount unchanged
                } else {
                    // xt && yt: pre both true -> post satisfied only by y
                    breakC[y]++;
                    // isSat remains true
                }
            }
        }
        assign[x] = oldVal ^ 1;
    };

    auto tryImprove = [&](int maxSteps, double walkProb, const chrono::steady_clock::time_point &endTime) {
        for (int step = 0; step < maxSteps; ++step) {
            if (unsatList.empty()) break;
            if ((step & 1023) == 0 && chrono::steady_clock::now() > endTime) break;

            int ci = unsatList[randIdx((int)unsatList.size())];
            Clause &c = clauses[ci];
            int x = c.v1, y = c.v2;

            if (c.type == 2) {
                // unit clause
                x = c.v1;
            } else {
                // choose between x and y
                if (randProb() < walkProb) {
                    // random choice
                    x = (rng() & 1) ? c.v1 : c.v2;
                } else {
                    int a = c.v1, b = c.v2;
                    int ba = breakC[a], bb = breakC[b];
                    int ma = makeC[a], mb = makeC[b];
                    int da = ma - ba, db = mb - bb;
                    if (da > db) x = a;
                    else if (db > da) x = b;
                    else {
                        if (ba < bb) x = a;
                        else if (bb < ba) x = b;
                        else x = (rng() & 1) ? a : b;
                    }
                }
            }
            flipVar(x);
        }
    };

    // Time budget (in milliseconds). We choose a conservative budget to avoid TLE.
    const int TIME_BUDGET_MS = 900;
    auto startTime = chrono::steady_clock::now();
    auto endTime = startTime + chrono::milliseconds(TIME_BUDGET_MS);

    // Multiple restarts
    int restart = 0;
    while (chrono::steady_clock::now() < endTime) {
        for (int i = 1; i <= n; ++i) assign[i] = randBool();
        initializeFromAssignment();
        if (satisfiedCount > bestSatisfied) {
            bestSatisfied = satisfiedCount;
            bestAssign = assign;
            if (bestSatisfied == m) break;
        }

        // Set parameters based on problem size
        int maxSteps = max(10000, min(2000000, 25 * max(1, m)));
        double walkProb = 0.3;

        tryImprove(maxSteps, walkProb, endTime);

        if (satisfiedCount > bestSatisfied) {
            bestSatisfied = satisfiedCount;
            bestAssign = assign;
            if (bestSatisfied == m) break;
        }
        restart++;
    }

    if (bestSatisfied < 0) {
        // m could be zero; just output zeros
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << int(bestAssign[i]);
    }
    cout << '\n';

    return 0;
}