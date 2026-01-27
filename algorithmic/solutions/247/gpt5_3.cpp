#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> A(N+1), B(N+1);
    for (int i = 1; i <= N; ++i) cin >> A[i];
    for (int i = 1; i <= N; ++i) cin >> B[i];

    long long sumA = 0, sumB = 0;
    for (int i = 1; i <= N; ++i) { sumA += A[i]; sumB += B[i]; }
    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }

    vector<long long> d(N+1), pref(N+1, 0);
    for (int i = 1; i <= N; ++i) d[i] = (long long)B[i] - (long long)A[i];
    long long cur = 0;
    for (int i = 1; i <= N; ++i) {
        cur += d[i];
        if (cur < 0) {
            cout << "No\n";
            return 0;
        }
    }

    vector<pair<int,int>> ops;
    for (int i = 1; i <= N; ++i) {
        if (d[i] <= 0) continue;
        for (int j = i+1; j <= N && d[i] > 0; ++j) {
            if (d[j] < 0) {
                long long t = min(d[i], -d[j]);
                for (long long k = 0; k < t; ++k) ops.emplace_back(i, j);
                d[i] -= t;
                d[j] += t;
            }
        }
        if (d[i] != 0) {
            cout << "No\n";
            return 0;
        }
    }

    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}