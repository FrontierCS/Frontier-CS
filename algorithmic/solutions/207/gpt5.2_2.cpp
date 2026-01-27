#include <bits/stdc++.h>
using namespace std;

static string toString128(__int128 x) {
    if (x == 0) return "0";
    bool neg = false;
    if (x < 0) { neg = true; x = -x; }
    string s;
    while (x > 0) {
        int d = (int)(x % 10);
        s.push_back(char('0' + d));
        x /= 10;
    }
    if (neg) s.push_back('-');
    reverse(s.begin(), s.end());
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; i++) cin >> S[i];

    int M;
    cin >> M;
    vector<int> X(M), Y(M);
    for (int i = 0; i < M; i++) cin >> X[i] >> Y[i];

    // Compute K_M and its inverse, where K_k = J_{k-1} ... J_0 (left composition)
    vector<int> K(N), invK(N);
    for (int i = 0; i < N; i++) K[i] = invK[i] = i;

    for (int j = 0; j < M; j++) {
        int x = X[j], y = Y[j];
        int px = invK[x], py = invK[y];
        swap(K[px], K[py]);
        swap(invK[x], invK[y]);
    }

    // P = K_M^{-1} ∘ S
    vector<int> P(N);
    for (int i = 0; i < N; i++) P[i] = invK[S[i]];

    // Decompose P into transpositions: for each cycle (c0 c1 ... cL-1),
    // P = (c0 cL-1)(c0 cL-2)...(c0 c1), so output in chronological order:
    // (c0 c1), (c0 c2), ..., (c0 cL-1)
    vector<char> vis(N, 0);
    vector<pair<int,int>> trans;
    trans.reserve(N);
    for (int i = 0; i < N; i++) {
        if (vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!vis[cur]) {
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = P[cur];
        }
        if ((int)cyc.size() <= 1) continue;
        int pivot = cyc[0];
        for (int t = 1; t < (int)cyc.size(); t++) trans.push_back({pivot, cyc[t]});
    }

    // Should hold by guarantee; safeguard in case of unexpected issues.
    if ((int)trans.size() > M) trans.resize(M);

    // Generate output swaps U_k = K_{k+1} V_k K_{k+1}^{-1}, where V_k is trans[k] or identity
    vector<int> KK(N), invKK(N);
    for (int i = 0; i < N; i++) KK[i] = invKK[i] = i;

    vector<int> outU(M), outV(M);
    long long sumCost = 0;

    for (int k = 0; k < M; k++) {
        // Update to K_{k+1} by applying Jerry swap J_k on outputs (swap values)
        int x = X[k], y = Y[k];
        int px = invKK[x], py = invKK[y];
        swap(KK[px], KK[py]);
        swap(invKK[x], invKK[y]);

        int a = 0, b = 0;
        if (k < (int)trans.size()) {
            a = trans[k].first;
            b = trans[k].second;
        }
        int u = KK[a];
        int v = KK[b];
        outU[k] = u;
        outV[k] = v;
        sumCost += llabs((long long)u - (long long)v);
    }

    __int128 V = (__int128)M * (__int128)sumCost;

    cout << M << '\n';
    for (int k = 0; k < M; k++) {
        cout << outU[k] << ' ' << outV[k] << '\n';
    }
    cout << toString128(V) << '\n';

    return 0;
}