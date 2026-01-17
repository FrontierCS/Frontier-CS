#include <bits/stdc++.h>
using namespace std;

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
    
    // Compute P_total^{-1} as p_inv by applying J in order: p_inv' = p_inv ∘ J
    vector<int> p_inv(N);
    iota(p_inv.begin(), p_inv.end(), 0);
    for (int i = 0; i < M; ++i) {
        int x = J[i].first, y = J[i].second;
        swap(p_inv[x], p_inv[y]);
    }
    
    // W_target = P_inv ∘ S0
    vector<int> W(N);
    for (int i = 0; i < N; ++i) {
        W[i] = p_inv[S[i]];
    }
    
    // Decompose W into transpositions
    vector<char> vis(N, 0);
    vector<pair<int,int>> transList;
    for (int i = 0; i < N; ++i) {
        if (!vis[i]) {
            int x = i;
            vector<int> cyc;
            while (!vis[x]) {
                vis[x] = 1;
                cyc.push_back(x);
                x = W[x];
            }
            if ((int)cyc.size() > 1) {
                int a0 = cyc[0];
                for (int j = 1; j < (int)cyc.size(); ++j) {
                    transList.emplace_back(a0, cyc[j]);
                }
            }
        }
    }
    int t = (int)transList.size();
    
    // Prepare tracking of images P_i(z) for z in support (W[z] != z)
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[i] = i;
    vector<int> r(N, -1);
    for (int i = 0; i < N; ++i) {
        if (W[i] != i) r[i] = i; // track elements in nontrivial cycles
    }
    
    long long sumDist = 0;
    int R = M;
    cout << R << '\n';
    int startIdx = M - t;
    int idxTrans = 0;
    for (int j = 0; j < M; ++j) {
        int u = J[j].first, v = J[j].second;
        int id1 = r[u], id2 = r[v];
        if (id1 != -1) pos[id1] = v;
        if (id2 != -1) pos[id2] = u;
        swap(r[u], r[v]);
        
        if (j < startIdx) {
            cout << 0 << ' ' << 0 << '\n';
        } else {
            int a = transList[idxTrans].first;
            int b = transList[idxTrans].second;
            int pa = pos[a];
            int pb = pos[b];
            cout << pa << ' ' << pb << '\n';
            sumDist += llabs((long long)pa - (long long)pb);
            idxTrans++;
        }
    }
    long long V = (long long)R * sumDist;
    cout << V << '\n';
    return 0;
}