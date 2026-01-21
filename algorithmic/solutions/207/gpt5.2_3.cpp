#include <bits/stdc++.h>
using namespace std;

static inline void append_ll(string &out, long long x) {
    if (x == 0) {
        out.push_back('0');
        return;
    }
    if (x < 0) {
        out.push_back('-');
        x = -x;
    }
    char buf[32];
    int n = 0;
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    while (n--) out.push_back(buf[n]);
}

static inline string to_string_i128(__int128 x) {
    if (x == 0) return "0";
    bool neg = false;
    if (x < 0) {
        neg = true;
        x = -x;
    }
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

    // T = S^{-1} as a permutation on positions: T[i] = position where value i is in initial array
    vector<int> T(N);
    for (int pos = 0; pos < N; pos++) T[S[pos]] = pos;

    // J_total as permutation on positions
    vector<int> J(N);
    iota(J.begin(), J.end(), 0);
    for (int k = 0; k < M; k++) {
        int a = X[k], b = Y[k];
        if (a != b) swap(J[a], J[b]);
    }

    // invJ = J_total^{-1}
    vector<int> invJ(N);
    for (int i = 0; i < N; i++) invJ[J[i]] = i;

    // U_target = invJ ∘ T
    vector<int> U_target(N);
    for (int i = 0; i < N; i++) U_target[i] = invJ[T[i]];

    // Decompose U_target into transpositions W_list in chronological order
    vector<char> vis(N, 0);
    vector<pair<int,int>> W_list;
    W_list.reserve(N);

    for (int i = 0; i < N; i++) {
        if (vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!vis[cur]) {
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = U_target[cur];
        }
        if (cyc.size() <= 1) continue;
        int base = cyc[0];
        for (int t = (int)cyc.size() - 1; t >= 1; --t) {
            W_list.push_back({base, cyc[t]});
        }
    }

    int L = (int)W_list.size();
    // Feasibility is guaranteed; for safety, if L > M, we still output M identity swaps (invalid cases shouldn't exist).
    if (L > M) L = M;

    // Compute our swaps U_k from W_k using suffix inverse permutations
    vector<int> invSuf(N);
    iota(invSuf.begin(), invSuf.end(), 0);

    vector<int> Uu(M), Uv(M);

    for (int k = M - 1; k >= 0; k--) {
        if (k < L) {
            int p = W_list[k].first;
            int q = W_list[k].second;
            Uu[k] = invSuf[p];
            Uv[k] = invSuf[q];
        } else {
            Uu[k] = 0;
            Uv[k] = 0;
        }
        int a = X[k], b = Y[k];
        if (a != b) swap(invSuf[a], invSuf[b]);
    }

    long long sumCost = 0;
    for (int k = 0; k < M; k++) sumCost += llabs((long long)Uu[k] - (long long)Uv[k]);
    __int128 V = (__int128)M * (__int128)sumCost;

    string out;
    out.reserve((size_t)(M + 3) * 20);

    append_ll(out, M);
    out.push_back('\n');
    for (int k = 0; k < M; k++) {
        append_ll(out, Uu[k]);
        out.push_back(' ');
        append_ll(out, Uv[k]);
        out.push_back('\n');
    }
    string vstr = to_string_i128(V);
    out.append(vstr);
    out.push_back('\n');

    cout << out;
    return 0;
}