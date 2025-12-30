#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    bool firstOutput = true;
    while (cin >> n) {
        if (n <= 0) continue;
        vector<long long> a;
        a.reserve(n);
        long long val;
        bool ok = true;
        for (long long i = 0; i < n; ++i) {
            if (!(cin >> val)) { ok = false; break; }
            a.push_back(val);
        }
        if (!ok) break;

        int N = (int)n;
        int v1 = N / 2;
        int v2 = v1 + 1;
        vector<int> pos(N + 1, -1);
        for (int i = 0; i < N; ++i) {
            if (a[i] >= 0 && a[i] <= N) {
                pos[(int)a[i]] = i + 1;
            }
        }
        int i1 = -1, i2 = -1;
        if (v1 >= 1 && v1 <= N) i1 = pos[v1];
        if (v2 >= 1 && v2 <= N) i2 = pos[v2];

        if (i1 == -1 || i2 == -1) {
            vector<pair<long long,int>> b;
            b.reserve(N);
            for (int i = 0; i < N; ++i) b.emplace_back(a[i], i + 1);
            sort(b.begin(), b.end());
            i1 = b[N/2 - 1].second;
            i2 = b[N/2].second;
        }

        if (i1 > i2) swap(i1, i2);
        if (!firstOutput) cout << '\n';
        cout << i1 << ' ' << i2;
        firstOutput = false;
    }
    return 0;
}