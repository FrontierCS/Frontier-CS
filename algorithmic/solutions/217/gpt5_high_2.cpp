#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    long long L = 1LL * N * M;
    vector<long long> rest;
    {
        long long x;
        while (cin >> x) rest.push_back(x);
    }
    
    auto output_groups_by_blocks = [&]() {
        for (int j = 0; j < M; ++j) {
            for (int c = 0; c < N; ++c) {
                if (c) cout << ' ';
                cout << (c * M + j + 1);
            }
            cout << '\n';
        }
    };
    
    if ((long long)rest.size() == L) {
        bool in1 = true, in0 = true;
        for (auto v : rest) {
            if (!(1 <= v && v <= N)) in1 = false;
            if (!(0 <= v && v < N)) in0 = false;
        }
        if (in1 || in0) {
            vector<vector<int>> buckets(N + 1);
            for (long long i = 0; i < L; ++i) {
                int col = (int)rest[i];
                if (in0) col += 1;
                if (col < 1 || col > N) { in1 = in0 = false; break; }
                buckets[col].push_back((int)i + 1);
            }
            bool ok = true;
            for (int c = 1; c <= N; ++c) if ((int)buckets[c].size() != M) { ok = false; break; }
            if (ok) {
                for (int t = 0; t < M; ++t) {
                    for (int c = 1; c <= N; ++c) {
                        if (c > 1) cout << ' ';
                        cout << buckets[c][t];
                    }
                    cout << '\n';
                }
                return 0;
            }
        }
    }
    
    // Fallback: assume indices are grouped by color in blocks of size M.
    output_groups_by_blocks();
    return 0;
}