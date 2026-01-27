#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<int> A(m), B(m);
    vector<vector<int>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        A[i] = a;
        B[i] = b;
        int va = abs(a), vb = abs(b);

        // Occurrence lists: avoid duplicating the same clause for the same variable
        if (va == vb) {
            occ[va].push_back(i);
        } else {
            occ[va].push_back(i);
            occ[vb].push_back(i);
        }

        if (a > 0) posCnt[va]++; else negCnt[va]++;
        if (b > 0) posCnt[vb]++; else negCnt[vb]++;
    }

    if (m == 0) {
        // Any assignment is optimal
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    vector<char> val(n + 1, 0);

    // Majority heuristic initial assignment
    for (int i = 1; i <= n; ++i) {
        if (posCnt[i] > negCnt[i]) val[i] = 1;
        else val[i] = 0;
    }

    auto evalClause = [&](int idx) -> bool {
        int a = A[idx], b = B[idx];
        int va = abs(a), vb = abs(b);
        bool aval = (a > 0) ? (bool)val[va] : !((bool)val[va]);
        bool bval = (b > 0) ? (bool)val[vb] : !((bool)val[vb]);
        return aval || bval;
    };

    vector<char> satisfied(m, 0);
    int satisfiedCount = 0;
    for (int i = 0; i < m; ++i) {
        bool sat = evalClause(i);
        satisfied[i] = sat;
        if (sat) ++satisfiedCount;
    }

    vector<char> bestVal = val;
    int bestSat = satisfiedCount;

    mt19937 rng(712367);
    uniform_int_distribution<int> distVar(1, n);
    uniform_int_distribution<int> dist100(0, 99);
    uniform_int_distribution<int> dist1000(0, 999);

    int maxIter = max(200000, 200 * n);

    for (int iter = 0; iter < maxIter && bestSat < m; ++iter) {
        int v = distVar(rng);

        int delta = 0;
        bool curV = val[v];
        bool newV = !curV;

        for (int idx : occ[v]) {
            bool before = satisfied[idx];
            int a = A[idx], b = B[idx];
            int va = abs(a), vb = abs(b);
            bool aval, bval;

            if (va == v) {
                aval = (a > 0) ? newV : !newV;
            } else {
                aval = (a > 0) ? (bool)val[va] : !((bool)val[va]);
            }
            if (vb == v) {
                bval = (b > 0) ? newV : !newV;
            } else {
                bval = (b > 0) ? (bool)val[vb] : !((bool)val[vb]);
            }

            bool after = aval || bval;
            if (before && !after) --delta;
            else if (!before && after) ++delta;
        }

        bool doFlip = false;
        if (delta > 0) {
            doFlip = true;
        } else if (delta == 0 && dist100(rng) < 5) { // 5% sideways moves
            doFlip = true;
        } else if (delta < 0 && dist1000(rng) < 1) { // rare downhill moves
            doFlip = true;
        }

        if (!doFlip) continue;

        val[v] = newV;

        for (int idx : occ[v]) {
            bool before = satisfied[idx];
            bool now = evalClause(idx);
            if (before != now) {
                if (now) ++satisfiedCount;
                else --satisfiedCount;
                satisfied[idx] = now;
            }
        }

        if (satisfiedCount > bestSat) {
            bestSat = satisfiedCount;
            bestVal = val;
            if (bestSat == m) break;
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << (bestVal[i] ? 1 : 0);
        if (i < n) cout << ' ';
    }
    cout << '\n';

    return 0;
}