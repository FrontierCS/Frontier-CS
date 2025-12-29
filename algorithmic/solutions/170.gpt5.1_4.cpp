#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    if (!(cin >> N >> L)) return 0;
    vector<int> T(N);
    for (int i = 0; i < N; i++) cin >> T[i];

    long long bestErr = (1LL << 60);
    vector<int> bestF(N);

    for (int K = 1; K <= N; K++) {
        double c = (double)L / K;
        vector<pair<double,int>> delta(N);
        for (int i = 0; i < N; i++) {
            double d = fabs(c - (double)T[i]) - (double)T[i];
            delta[i] = {d, i};
        }
        sort(delta.begin(), delta.end(), [](const pair<double,int>& a, const pair<double,int>& b) {
            if (a.first != b.first) return a.first < b.first;
            return a.second < b.second;
        });

        vector<int> S(K);
        for (int j = 0; j < K; j++) S[j] = delta[j].second;

        vector<int> f(N);
        int root = S[0];
        for (int i = 0; i < N; i++) f[i] = root;
        for (int j = 0; j < K; j++) {
            int u = S[j];
            int v = S[(j + 1) % K];
            f[u] = v;
        }

        vector<int> cnt(N, 0);
        int cur = 0;
        for (int w = 0; w < L; w++) {
            cnt[cur]++;
            cur = f[cur];
        }

        long long err = 0;
        for (int i = 0; i < N; i++) {
            err += llabs((long long)cnt[i] - (long long)T[i]);
        }

        if (err < bestErr) {
            bestErr = err;
            bestF = f;
        }
    }

    for (int i = 0; i < N; i++) {
        int v = bestF[i];
        cout << v << " " << v << "\n";
    }

    return 0;
}