#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int N, R;
    cin >> N >> R;
    vector<int> U(N), V(N);
    vector<int> parent(2 * N + 1, -1);
    for (int i = 0; i < N; i++) {
        cin >> U[i] >> V[i];
        parent[U[i]] = i;
        parent[V[i]] = i;
    }
    string gtype(N, ' ');
    auto force = [&](auto&& self, int sub, int val, string& qs) -> void {
        if (sub >= N) {
            qs[sub] = '0' + val;
            return;
        }
        qs[sub] = '0';
        self(self, U[sub], val, qs);
        self(self, V[sub], val, qs);
    };
    auto test = [&](int k) -> void {
        vector<int> path;
        for (int t = k; t != -1; t = parent[t]) {
            path.push_back(t);
        }
        // path[0] = k, ... path.back() = 0
        string qs(2 * N + 1, ' ');
        for (int p : path) qs[p] = '0';
        force(force, U[k], 0, qs);
        force(force, V[k], 1, qs);
        for (size_t i = 1; i < path.size(); ++i) {
            int pi = path[i];
            int sigc = path[i - 1];
            int oc = (U[pi] == sigc ? V[pi] : U[pi]);
            int sval = (gtype[pi] == '&' ? 1 : 0);
            force(force, oc, sval, qs);
        }
        cout << "?";
        for (char c : qs) cout << c;
        cout << endl;
        cout.flush();
        int res;
        cin >> res;
        gtype[k] = (res == 0 ? '&' : '|');
    };
    function<void(int)> solve = [&](int node) {
        test(node);
        int l = U[node], r = V[node];
        if (l < N) solve(l);
        if (r < N) solve(r);
    };
    solve(0);
    cout << "!";
    for (char c : gtype) cout << c;
    cout << endl;
    cout.flush();
    return 0;
}