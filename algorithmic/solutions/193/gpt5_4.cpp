#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int lit[2]; // literal values as signed ints: +x or -x (1-based)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<pair<int, uint8_t>>> occ(n); // for each var, list of (clause index, side 0/1)
    vector<int> posCnt(n, 0), negCnt(n, 0);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clauses[i].lit[0] = a;
        clauses[i].lit[1] = b;
        int va = (a > 0 ? a - 1 : -a - 1);
        int vb = (b > 0 ? b - 1 : -b - 1);
        occ[va].push_back({i, 0});
        occ[vb].push_back({i, 1});
        if (a > 0) posCnt[va]++; else negCnt[va]++;
        if (b > 0) posCnt[vb]++; else negCnt[vb]++;
    }

    // Random generator
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    vector<char> assign(n, 0), bestAssign(n, 0);
    for (int i = 0; i < n; ++i) {
        if (posCnt[i] > negCnt[i]) assign[i] = 1;
        else if (posCnt[i] < negCnt[i]) assign[i] = 0;
        else assign[i] = (char)(rng() & 1);
    }

    vector<int> t(m, 0); // number of satisfied literals in clause
    vector<int> unsatPos(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);

    auto addUnsat = [&](int ci) {
        if (unsatPos[ci] != -1) return;
        unsatPos[ci] = (int)unsatList.size();
        unsatList.push_back(ci);
    };
    auto removeUnsat = [&](int ci) {
        int p = unsatPos[ci];
        if (p == -1) return;
        int q = unsatList.back();
        unsatList[p] = q;
        unsatPos[q] = p;
        unsatList.pop_back();
        unsatPos[ci] = -1;
    };

    // Initial evaluation
    int S = 0;
    for (int i = 0; i < m; ++i) {
        int l0 = clauses[i].lit[0], l1 = clauses[i].lit[1];
        int v0 = (l0 > 0 ? l0 - 1 : -l0 - 1);
        int v1 = (l1 > 0 ? l1 - 1 : -l1 - 1);
        bool p0 = l0 > 0, p1 = l1 > 0;
        bool s0 = (assign[v0] == p0);
        bool s1 = (assign[v1] == p1);
        t[i] = (int)s0 + (int)s1;
        if (t[i] == 0) addUnsat(i);
    }
    S = m - (int)unsatList.size();

    vector<int> brk(n, 0); // break count: number of clauses that would become unsatisfied if flipping var
    for (int i = 0; i < m; ++i) {
        int l0 = clauses[i].lit[0], l1 = clauses[i].lit[1];
        int v0 = (l0 > 0 ? l0 - 1 : -l0 - 1);
        int v1 = (l1 > 0 ? l1 - 1 : -l1 - 1);
        bool p0 = l0 > 0, p1 = l1 > 0;
        bool s0 = (assign[v0] == p0);
        bool s1 = (assign[v1] == p1);
        if (v0 != v1) {
            if (s0 && !s1) brk[v0]++;
            if (s1 && !s0) brk[v1]++;
        } else {
            // same variable appears twice
            if (p0 == p1) {
                // x v x or ~x v ~x -> clause satisfied iff that literal true (both true), unsatisfied if false
                if (s0 && s1) brk[v0]++;
            } else {
                // x v ~x tautology -> no effect
            }
        }
    }

    bestAssign = assign;
    int bestS = S;

    vector<int> visited(m, 0);
    int visitId = 1;

    auto flipVar = [&](int v) {
        visitId++;
        if (visitId == 0) { // unlikely; reset to avoid overflow on extremely long runs
            visitId = 1;
            fill(visited.begin(), visited.end(), 0);
        }
        for (auto &pr : occ[v]) {
            int ci = pr.first;
            if (visited[ci] == visitId) continue;
            visited[ci] = visitId;

            int l0 = clauses[ci].lit[0], l1 = clauses[ci].lit[1];
            int aVar = (l0 > 0 ? l0 - 1 : -l0 - 1);
            int bVar = (l1 > 0 ? l1 - 1 : -l1 - 1);
            bool aPos = l0 > 0, bPos = l1 > 0;

            bool aTrueBefore = (assign[aVar] == aPos);
            bool bTrueBefore = (assign[bVar] == bPos);
            int tbefore = (int)aTrueBefore + (int)bTrueBefore;

            bool aTrueAfter = aTrueBefore;
            bool bTrueAfter = bTrueBefore;
            if (aVar == v) aTrueAfter = !aTrueAfter;
            if (bVar == v) bTrueAfter = !bTrueAfter;
            int tafter = (int)aTrueAfter + (int)bTrueAfter;

            if (tbefore == 0 && tafter > 0) {
                removeUnsat(ci);
                S++;
            } else if (tbefore > 0 && tafter == 0) {
                addUnsat(ci);
                S--;
            }

            if (aVar == bVar) {
                int w = aVar;
                if (aPos == bPos) {
                    bool contribBefore = (tbefore == 2);
                    bool contribAfter  = (tafter == 2);
                    brk[w] += (int)contribAfter - (int)contribBefore;
                } else {
                    // tautology: no contribution to break
                }
            } else {
                bool contribBefA = aTrueBefore && !bTrueBefore;
                bool contribBefB = bTrueBefore && !aTrueBefore;
                bool contribAftA = aTrueAfter && !bTrueAfter;
                bool contribAftB = bTrueAfter && !aTrueAfter;
                brk[aVar] += (int)contribAftA - (int)contribBefA;
                brk[bVar] += (int)contribAftB - (int)contribBefB;
            }

            t[ci] = tafter;
        }
        assign[v] ^= 1;
    };

    // WalkSAT-like local search
    const double noise = 0.5;
    auto startTime = chrono::steady_clock::now();
    const double timeLimitSec = 0.9; // conservative time budget
    const uint64_t timeCheckInterval = 4096;
    uint64_t iter = 0;

    while (true) {
        if (unsatList.empty()) {
            bestAssign = assign;
            bestS = S;
            break;
        }

        int cidx = unsatList[rng() % unsatList.size()];
        int l0 = clauses[cidx].lit[0], l1 = clauses[cidx].lit[1];
        int v0 = (l0 > 0 ? l0 - 1 : -l0 - 1);
        int v1 = (l1 > 0 ? l1 - 1 : -l1 - 1);

        int chosen;
        if (v0 == v1) {
            chosen = v0;
        } else {
            int b0 = brk[v0], b1 = brk[v1];
            if (b0 == 0 && b1 == 0) {
                chosen = (rng() & 1) ? v0 : v1;
            } else if (b0 == 0 || b1 == 0) {
                chosen = (b0 == 0) ? v0 : v1;
            } else {
                if (uniform_real_distribution<double>(0.0, 1.0)(rng) < noise) {
                    chosen = (rng() & 1) ? v0 : v1;
                } else {
                    if (b0 < b1) chosen = v0;
                    else if (b1 < b0) chosen = v1;
                    else chosen = (rng() & 1) ? v0 : v1;
                }
            }
        }

        flipVar(chosen);

        if (S > bestS) {
            bestS = S;
            bestAssign = assign;
            if (bestS == m) break; // can't do better
        }

        ++iter;
        if ((iter & (timeCheckInterval - 1)) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            if (elapsed > timeLimitSec) break;
        }
    }

    // Output best assignment found
    for (int i = 0; i < n; ++i) {
        cout << (bestAssign[i] ? 1 : 0) << (i + 1 == n ? '\n' : ' ');
    }

    return 0;
}