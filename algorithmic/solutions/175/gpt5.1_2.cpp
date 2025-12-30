#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<int> a, b, c;
vector<int> startPos;          // size n+2
vector<int> occClause;         // size 3*m
vector<unsigned char> occPos;  // which literal (0,1,2) in clause

vector<unsigned char> assignVal;     // current assignment 0/1 for vars 1..n
vector<unsigned char> bestAssignVal; // best found assignment
vector<unsigned char> trueCnt;       // number of true literals in each clause (0..3)

vector<int> unsat;             // indices of unsatisfied clauses
vector<int> unsatIndex;        // -1 if satisfied, else position in unsat

mt19937_64 rng;

// mark clause as unsatisfied
inline void makeUnsat(int cid) {
    if (unsatIndex[cid] != -1) return;
    unsatIndex[cid] = (int)unsat.size();
    unsat.push_back(cid);
}

// mark clause as satisfied
inline void makeSat(int cid) {
    int pos = unsatIndex[cid];
    if (pos == -1) return;
    int last = unsat.back();
    unsat[pos] = last;
    unsatIndex[last] = pos;
    unsat.pop_back();
    unsatIndex[cid] = -1;
}

// flip variable v to newVal (0 or 1)
inline void flipVar(int v, unsigned char newVal) {
    unsigned char oldVal = assignVal[v];
    if (oldVal == newVal) return;
    assignVal[v] = newVal;

    int begin = startPos[v];
    int end   = startPos[v + 1];

    for (int idx = begin; idx < end; ++idx) {
        int cid = occClause[idx];
        unsigned char pos = occPos[idx];
        int lit;
        if (pos == 0) lit = a[cid];
        else if (pos == 1) lit = b[cid];
        else lit = c[cid];

        bool beforeTrue, afterTrue;
        if (lit > 0) {
            beforeTrue = (oldVal != 0);
            afterTrue  = (newVal != 0);
        } else {
            beforeTrue = !(oldVal != 0);
            afterTrue  = !(newVal != 0);
        }

        if (beforeTrue == afterTrue) continue;

        unsigned char oldCnt = trueCnt[cid];
        if (beforeTrue) {
            unsigned char newCnt = (unsigned char)(oldCnt - 1);
            trueCnt[cid] = newCnt;
            if (oldCnt == 1) { // becomes 0
                makeUnsat(cid);
            }
        } else { // beforeFalse, afterTrue
            unsigned char newCnt = (unsigned char)(oldCnt + 1);
            trueCnt[cid] = newCnt;
            if (oldCnt == 0) { // becomes 1
                makeSat(cid);
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto startTime = chrono::steady_clock::now();
    rng.seed(chrono::steady_clock::now().time_since_epoch().count());

    if (!(cin >> n >> m)) {
        return 0;
    }

    a.resize(m);
    b.resize(m);
    c.resize(m);

    vector<int> deg(n + 1, 0);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int x, y, z;
        cin >> x >> y >> z;
        a[i] = x;
        b[i] = y;
        c[i] = z;

        deg[abs(x)]++;
        deg[abs(y)]++;
        deg[abs(z)]++;

        if (x > 0) posCnt[x]++; else negCnt[-x]++;
        if (y > 0) posCnt[y]++; else negCnt[-y]++;
        if (z > 0) posCnt[z]++; else negCnt[-z]++;
    }

    // Build occurrence lists
    startPos.assign(n + 2, 0);
    for (int v = 1; v <= n; ++v) {
        startPos[v + 1] = startPos[v] + deg[v];
    }
    int totalOcc = startPos[n + 1];
    occClause.resize(totalOcc);
    occPos.resize(totalOcc);
    vector<int> nextPos(n + 1, 0);
    for (int v = 1; v <= n; ++v) nextPos[v] = startPos[v];

    for (int cid = 0; cid < m; ++cid) {
        int lits[3] = {a[cid], b[cid], c[cid]};
        for (int p = 0; p < 3; ++p) {
            int v = abs(lits[p]);
            int idx = nextPos[v]++;
            occClause[idx] = cid;
            occPos[idx] = (unsigned char)p;
        }
    }

    assignVal.assign(n + 1, 0);
    bestAssignVal.assign(n + 1, 0);
    trueCnt.assign(m, 0);
    unsatIndex.assign(m, -1);
    unsat.clear();
    unsat.reserve(m / 4 + 10);

    // Initial assignment: majority of positive vs negative occurrences
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] > negCnt[v]) assignVal[v] = 1;
        else if (posCnt[v] < negCnt[v]) assignVal[v] = 0;
        else assignVal[v] = (unsigned char)(rng() & 1);
    }

    // Evaluate initial assignment
    for (int cid = 0; cid < m; ++cid) {
        int lit1 = a[cid];
        int lit2 = b[cid];
        int lit3 = c[cid];
        int cnt = 0;
        if (lit1 > 0) cnt += (assignVal[lit1] != 0);
        else          cnt += !(assignVal[-lit1] != 0);
        if (lit2 > 0) cnt += (assignVal[lit2] != 0);
        else          cnt += !(assignVal[-lit2] != 0);
        if (lit3 > 0) cnt += (assignVal[lit3] != 0);
        else          cnt += !(assignVal[-lit3] != 0);

        trueCnt[cid] = (unsigned char)cnt;
        if (cnt == 0) {
            unsatIndex[cid] = (int)unsat.size();
            unsat.push_back(cid);
        }
    }

    bestAssignVal = assignVal;
    int bestUnsat = (int)unsat.size();

    const double TIME_LIMIT = 0.95; // seconds (total, including input)

    if (m > 0 && bestUnsat > 0) {
        while (true) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            if (elapsed > TIME_LIMIT) break;
            if (unsat.empty()) break;

            int cid = unsat[rng() % unsat.size()];
            int pick = (int)(rng() % 3);
            int lit;
            if (pick == 0) lit = a[cid];
            else if (pick == 1) lit = b[cid];
            else lit = c[cid];

            int var = (lit > 0) ? lit : -lit;
            unsigned char newVal = (lit > 0) ? 1 : 0;

            flipVar(var, newVal);

            int curUnsat = (int)unsat.size();
            if (curUnsat < bestUnsat) {
                bestUnsat = curUnsat;
                bestAssignVal = assignVal;
                if (bestUnsat == 0) break;
            }
        }
    }

    // Output best assignment found
    if (n >= 1) {
        cout << (int)bestAssignVal[1];
        for (int v = 2; v <= n; ++v) {
            cout << ' ' << (int)bestAssignVal[v];
        }
    }
    cout << '\n';

    return 0;
}