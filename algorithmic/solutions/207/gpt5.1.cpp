#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];

    // S_inv[value] = position of that value in initial array
    vector<int> S_inv(N);
    for (int i = 0; i < N; ++i) {
        int v = S[i];
        S_inv[v] = i;
    }

    int M;
    cin >> M;
    vector<pair<int,int>> jerry(M);
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        jerry[i] = {x, y};
    }

    // Compute T_inv: effect of all Jerry swaps (positions -> original indices, then inverted)
    vector<int> orig_at_pos(N);
    for (int i = 0; i < N; ++i) orig_at_pos[i] = i;
    for (int k = 0; k < M; ++k) {
        int x = jerry[k].first;
        int y = jerry[k].second;
        swap(orig_at_pos[x], orig_at_pos[y]);
    }
    // T(pos) = orig_at_pos[pos]; T_inv(orig) = position
    vector<int> T_inv(N);
    for (int pos = 0; pos < N; ++pos) {
        int orig = orig_at_pos[pos];
        T_inv[orig] = pos;
    }

    // P' = S_inv ∘ T_inv
    vector<int> P(N);
    for (int x = 0; x < N; ++x) {
        P[x] = S_inv[ T_inv[x] ];
    }

    // Decompose P into transpositions
    vector<char> vis(N, 0);
    vector<pair<int,int>> trans; // transpositions representing P'
    trans.reserve(N);
    for (int i = 0; i < N; ++i) {
        if (vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!vis[cur]) {
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = P[cur];
        }
        int L = (int)cyc.size();
        if (L > 1) {
            int v0 = cyc[0];
            for (int t = L - 1; t >= 1; --t) {
                trans.emplace_back(v0, cyc[t]);
            }
        }
    }
    int K = (int)trans.size();
    // By problem guarantee, K <= M

    // Now compute our actual swaps ρ_k using prefix Jerry permutations
    vector<pair<int,int>> our_swaps(M);
    vector<int> pos_of_orig(N), cur_orig_at_pos(N);
    for (int i = 0; i < N; ++i) {
        pos_of_orig[i] = i;      // position of original index i after prefix of Jerry swaps
        cur_orig_at_pos[i] = i;  // original index at position i
    }

    long long sumdist = 0;
    int idxTrans = 0;

    for (int k = 0; k < M; ++k) {
        int x = jerry[k].first;
        int y = jerry[k].second;

        // Apply Jerry's swap to prefix simulation (J-only)
        int origX = cur_orig_at_pos[x];
        int origY = cur_orig_at_pos[y];
        cur_orig_at_pos[x] = origY;
        cur_orig_at_pos[y] = origX;
        pos_of_orig[origX] = y;
        pos_of_orig[origY] = x;

        if (idxTrans < K) {
            int a = trans[idxTrans].first;
            int b = trans[idxTrans].second;
            int pa = pos_of_orig[a];
            int pb = pos_of_orig[b];
            our_swaps[k] = {pa, pb};
            sumdist += llabs((long long)pa - (long long)pb);
            ++idxTrans;
        } else {
            our_swaps[k] = {0, 0}; // identity swap
        }
    }

    long long R = M;
    long long V = R * sumdist;

    cout << R << '\n';
    for (int k = 0; k < M; ++k) {
        cout << our_swaps[k].first << ' ' << our_swaps[k].second << '\n';
    }
    cout << V << '\n';

    return 0;
}