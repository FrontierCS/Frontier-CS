#include <bits/stdc++.h>
using namespace std;

void solve(const vector<int>& positions, const vector<int>& values, vector<int>& perm, int n) {
    int m = positions.size();
    if (m <= 1) {
        if (m == 1) {
            perm[positions[0]] = values[0];
        }
        return;
    }
    int m1 = m / 2;
    vector<int> pos1(positions.begin(), positions.begin() + m1);
    vector<int> pos2(positions.begin() + m1, positions.end());
    vector<int> xs(m);
    for (int idx = 0; idx < m; idx++) {
        int k = values[idx];
        vector<int> Q(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            if (perm[i] != 0) {
                Q[i] = perm[i];
            } else {
                Q[i] = i;
            }
        }
        for (int p : pos1) {
            Q[p] = k;
        }
        cout << 0;
        for (int i = 1; i <= n; i++) {
            cout << " " << Q[i];
        }
        cout << endl;
        cout.flush();
        int resp;
        cin >> resp;
        xs[idx] = resp;
    }
    int maxx = 0;
    for (int r : xs) {
        maxx = max(maxx, r);
    }
    vector<int> w1;
    for (int idx = 0; idx < m; idx++) {
        if (xs[idx] == maxx) {
            w1.push_back(values[idx]);
        }
    }
    set<int> w1s(w1.begin(), w1.end());
    vector<int> w2;
    for (int v : values) {
        if (w1s.find(v) == w1s.end()) {
            w2.push_back(v);
        }
    }
    solve(pos1, w1, perm, n);
    solve(pos2, w2, perm, n);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<int> perm(n + 1, 0);
    vector<int> allp(n), allv(n);
    for (int i = 0; i < n; i++) {
        allp[i] = i + 1;
        allv[i] = i + 1;
    }
    solve(allp, allv, perm, n);
    cout << 1;
    for (int i = 1; i <= n; i++) {
        cout << " " << perm[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}