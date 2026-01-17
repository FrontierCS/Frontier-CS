#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

ll query(int u, int d) {
    cout << "? " << u << " " << d << endl;
    ll res;
    cin >> res;
    return res;
}

int main() {
    int h;
    cin >> h;
    int n = (1 << h) - 1;
    
    if (h == 2) {
        vector<ll> res(4);
        for (int u = 1; u <= 3; u++) {
            res[u] = query(u, 1);
        }
        ll mn = min({res[1], res[2], res[3]});
        ll mx = max({res[1], res[2], res[3]});
        ll S = mn + mx;
        cout << "! " << S << endl;
        return 0;
    }
    
    vector<ll> r1(n + 1);
    ll D = 0;
    for (int u = 1; u <= n; u++) {
        r1[u] = query(u, 1);
        D += r1[u];
    }
    
    vector<int> indices(n);
    iota(indices.begin(), indices.end(), 1);
    random_shuffle(indices.begin(), indices.end());
    int sample = min(n, 1000);
    
    vector<int> candidates;
    for (int i = 0; i < sample; i++) {
        int u = indices[i];
        bool ok = true;
        for (int d = h; d <= 2 * h - 2; d++) {
            if (query(u, d) != 0) {
                ok = false;
                break;
            }
        }
        if (ok) candidates.push_back(u);
    }
    
    if (candidates.empty()) {
        cout << "! " << 0 << endl;
        return 0;
    }
    
    for (int u_root : candidates) {
        vector<ll> A(h); // index 1..h-1
        for (int d = 1; d < h; d++) {
            A[d] = query(u_root, d);
        }
        for (int i = 0; i < sample; i++) {
            int u = indices[i];
            if (u == u_root) continue;
            for (int j = i + 1; j < sample; j++) {
                int v = indices[j];
                if (v == u_root) continue;
                if (h - 1 >= 2) {
                    ll f1_est = (r1[u] + r1[v] - A[2]);
                    if (f1_est % 2 != 0) continue;
                    f1_est /= 2;
                    if (f1_est < 0) continue;
                    if (f1_est > r1[u] || f1_est > r1[v]) continue;
                    ll S_est = f1_est;
                    for (int d = 1; d < h; d++) S_est += A[d];
                    cout << "! " << S_est << endl;
                    return 0;
                }
            }
        }
    }
    
    cout << "! " << D / 2 << endl;
    return 0;
}