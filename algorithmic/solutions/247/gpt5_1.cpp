#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> A(N), B(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];

    long long sumA = 0, sumB = 0;
    for (int i = 0; i < N; ++i) { sumA += A[i]; sumB += B[i]; }
    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }

    vector<long long> D(N);
    for (int i = 0; i < N; ++i) D[i] = B[i] - A[i];

    long long pref = 0;
    for (int i = 0; i < N; ++i) {
        pref += D[i];
        if (pref < 0) {
            cout << "No\n";
            return 0;
        }
    }

    vector<pair<int,long long>> donors;
    for (int i = 0; i < N; ++i) if (D[i] < 0) donors.emplace_back(i, -D[i]);

    vector<pair<int,int>> ops;
    int p = 0;
    for (int i = 0; i < N; ++i) if (D[i] > 0) {
        long long need = D[i];
        while (need > 0) {
            while (p < (int)donors.size() && (donors[p].second == 0 || donors[p].first <= i)) ++p;
            if (p >= (int)donors.size()) {
                cout << "No\n";
                return 0;
            }
            int j = donors[p].first;
            long long give = min(need, donors[p].second);
            for (long long t = 0; t < give; ++t) ops.emplace_back(i + 1, j + 1);
            need -= give;
            donors[p].second -= give;
        }
    }

    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto &e : ops) cout << e.first << " " << e.second << "\n";
    return 0;
}