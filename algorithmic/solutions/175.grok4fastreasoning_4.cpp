#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<int> lits(3 * m);
    for (int i = 0; i < 3 * m; i++) {
        cin >> lits[i];
    }
    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << " ";
            cout << 0;
        }
        cout << "\n";
        return 0;
    }
    srand(time(NULL));
    int best_s = -1;
    vector<int> best(n + 1, 0);
    auto evaluate = [&](const vector<int>& assignment) -> int {
        int satisfied = 0;
        for (int i = 0; i < m; i++) {
            int a = lits[3 * i], b = lits[3 * i + 1], c = lits[3 * i + 2];
            int va = abs(a), vb = abs(b), vc = abs(c);
            bool sa = (a > 0) ? assignment[va] : !assignment[va];
            bool sb = (b > 0) ? assignment[vb] : !assignment[vb];
            bool sc = (c > 0) ? assignment[vc] : !assignment[vc];
            if (sa || sb || sc) satisfied++;
        }
        return satisfied;
    };
    // all false
    vector<int> ass0(n + 1, 0);
    int s0 = evaluate(ass0);
    best_s = s0;
    best = ass0;
    // all true
    vector<int> ass1(n + 1, 1);
    int s1 = evaluate(ass1);
    if (s1 > best_s) {
        best_s = s1;
        best = ass1;
    }
    // random
    for (int trial = 0; trial < 128; trial++) {
        vector<int> assignment(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            assignment[i] = rand() % 2;
        }
        int s = evaluate(assignment);
        if (s > best_s) {
            best_s = s;
            best = assignment;
        }
    }
    // output
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << best[i];
    }
    cout << "\n";
    return 0;
}