#include <bits/stdc++.h>
using namespace std;

static inline int count_cycles(const vector<int>& p) {
    int n = (int)p.size();
    vector<char> vis(n, 0);
    int cycles = 0;
    for (int i = 0; i < n; ++i) {
        if (!vis[i]) {
            ++cycles;
            int v = i;
            while (!vis[v]) {
                vis[v] = 1;
                v = p[v];
            }
        }
    }
    return cycles;
}

static inline int min_swaps_to_sort_after_prefix(const vector<int>& S, const vector<pair<int,int>>& J, int R) {
    int n = (int)S.size();
    vector<int> s = S;
    for (int i = 0; i < R; ++i) {
        int x = J[i].first, y = J[i].second;
        swap(s[x], s[y]);
    }
    int cycles = count_cycles(s);
    return n - cycles;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];
    int M;
    cin >> M;
    vector<pair<int,int>> J(M);
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        J[i] = {x, y};
    }
    
    // Binary search minimal R such that R >= min_swaps_to_sort_after_prefix(R)
    int low = 0, high = M;
    while (low < high) {
        int mid = (low + high) >> 1;
        int mreq = min_swaps_to_sort_after_prefix(S, J, mid);
        if (mid >= mreq) high = mid;
        else low = mid + 1;
    }
    int R = low;
    
    // Compute S after first R Jerry swaps
    vector<int> SR = S;
    for (int i = 0; i < R; ++i) {
        swap(SR[J[i].first], SR[J[i].second]);
    }
    
    // Decompose T = (SR)^{-1} into transpositions:
    // For each cycle (c0 c1 ... ck), T decomposition: (c0 c1)(c0 c2)...(c0 ck)
    int cycles = count_cycles(SR);
    int L = N - cycles;
    vector<pair<int,int>> trans_by_round(R, {-1, -1}); // store T_i for each round i (identity by default)
    
    // Build decomposition list
    vector<char> vis(N, 0);
    vector<pair<int,int>> decomp;
    decomp.reserve(max(0, L));
    for (int i = 0; i < N; ++i) {
        if (!vis[i]) {
            int v = i;
            vector<int> cyc;
            while (!vis[v]) {
                vis[v] = 1;
                cyc.push_back(v);
                v = SR[v];
            }
            if ((int)cyc.size() > 1) {
                int c0 = cyc[0];
                for (size_t t = 1; t < cyc.size(); ++t) {
                    decomp.emplace_back(c0, cyc[t]);
                }
            }
        }
    }
    // Place these L transpositions at the last L rounds
    for (int k = 0; k < L; ++k) {
        trans_by_round[R - L + k] = decomp[k];
    }
    
    // Compute our swaps O_i = Suf_i ∘ T_i ∘ Suf_i^{-1}
    // Maintain suffix mapping Suf_i via arrays A (domain->codomain) and B (codomain->domain)
    vector<int> A(N), B(N);
    for (int i = 0; i < N; ++i) { A[i] = i; B[i] = i; }
    
    vector<pair<int,int>> our_ops(R);
    long long sumCost = 0;
    for (int i = R - 1; i >= 0; --i) {
        int u = 0, v = 0;
        if (trans_by_round[i].first != -1) {
            int p = trans_by_round[i].first;
            int q = trans_by_round[i].second;
            u = A[p];
            v = A[q];
            sumCost += llabs((long long)u - (long long)v);
        } else {
            u = v = 0; // identity
        }
        our_ops[i] = {u, v};
        
        // Update suffix mapping: Suf_{i-1} = J_i ∘ Suf_i
        int x = J[i].first, y = J[i].second;
        int tX = B[x], tY = B[y];
        // swap images at these preimages
        swap(A[tX], A[tY]);
        // update inverses
        swap(B[x], B[y]);
    }
    
    // Output
    cout << R << "\n";
    for (int i = 0; i < R; ++i) {
        cout << our_ops[i].first << " " << our_ops[i].second << "\n";
    }
    __int128 V128 = (__int128)R * ( (__int128)sumCost );
    long long V = (long long)V128;
    cout << V << "\n";
    
    return 0;
}