#include <bits/stdc++.h>
using namespace std;

using U64 = unsigned long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<int> U(M), V(M);
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; i++) {
        cin >> U[i] >> V[i];
        adj[U[i]].push_back(V[i]);
        adj[V[i]].push_back(U[i]);
    }

    int W = (N + 63) / 64;
    vector<U64> fullMask(W, ~0ULL);
    if (N % 64) fullMask[W - 1] = (N % 64 == 0) ? ~0ULL : ((1ULL << (N % 64)) - 1);

    auto new_bitset = [&](bool all_ones) {
        vector<U64> b(W, 0);
        if (all_ones) {
            for (int i = 0; i < W; ++i) b[i] = fullMask[i];
        }
        return b;
    };

    auto bitset_and_inplace = [&](vector<U64>& a, const vector<U64>& b) {
        for (int i = 0; i < W; ++i) a[i] &= b[i];
    };
    auto bitset_andnot_inplace = [&](vector<U64>& a, const vector<U64>& b) {
        for (int i = 0; i < W; ++i) a[i] &= (~b[i]) & fullMask[i];
    };
    auto bitset_or_inplace = [&](vector<U64>& a, const vector<U64>& b) {
        for (int i = 0; i < W; ++i) a[i] |= b[i];
    };
    auto bitset_setbit = [&](vector<U64>& a, int idx) {
        a[idx >> 6] |= (1ULL << (idx & 63));
    };
    auto bitset_clearbit = [&](vector<U64>& a, int idx) {
        a[idx >> 6] &= ~(1ULL << (idx & 63));
    };
    auto bitset_popcount = [&](const vector<U64>& a) -> long long {
        long long s = 0;
        for (int i = 0; i < W; ++i) s += __builtin_popcountll(a[i]);
        return s;
    };
    auto bitset_any = [&](const vector<U64>& a) -> bool {
        for (int i = 0; i < W; ++i) if (a[i]) return true;
        return false;
    };

    // Candidate set for B for each possible A.
    vector<vector<U64>> cand(N, new_bitset(true));
    for (int a = 0; a < N; ++a) {
        bitset_clearbit(cand[a], a); // A != B
    }

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto build_orientation_and_reach = [&](const vector<int>& pos, vector<int>& qbits, vector<vector<U64>>& reach) {
        qbits.assign(M, 0);
        vector<vector<int>> outs(N);
        for (int i = 0; i < M; i++) {
            int a = U[i], b = V[i];
            if (pos[a] > pos[b]) {
                // a -> b
                outs[a].push_back(b);
                qbits[i] = 0; // 0 means U->V
            } else {
                // b -> a
                outs[b].push_back(a);
                qbits[i] = 1; // 1 means V->U
            }
        }
        vector<int> ord(N);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int x, int y){ return pos[x] < pos[y]; });

        reach.assign(N, new_bitset(false));
        for (int u = 0; u < N; ++u) bitset_setbit(reach[u], u);
        for (int idx = 0; idx < N; ++idx) {
            int u = ord[idx];
            for (int v : outs[u]) {
                bitset_or_inplace(reach[u], reach[v]);
            }
        }
    };

    auto ask_query = [&](const vector<int>& qbits) -> int {
        cout << 0;
        for (int i = 0; i < M; i++) {
            cout << ' ' << qbits[i];
        }
        cout << '\n';
        cout.flush();
        int x;
        if (!(cin >> x)) return -1;
        return x;
    };

    auto try_output_answer = [&](const vector<vector<U64>>& cands) -> bool {
        int A = -1, B = -1;
        for (int a = 0; a < N; ++a) {
            for (int w = 0; w < W; ++w) {
                U64 word = cands[a][w];
                while (word) {
                    int b = (w << 6) + __builtin_ctzll(word);
                    if (A == -1) {
                        A = a; B = b;
                    } else {
                        // More than one candidate
                        return false;
                    }
                    word &= word - 1;
                }
            }
        }
        if (A != -1 && B != -1) {
            cout << 1 << ' ' << A << ' ' << B << '\n';
            cout.flush();
            return true;
        }
        return false;
    };

    int max_queries = 600;
    int used_queries = 0;

    while (used_queries + 1 <= max_queries) {
        // Build random permutation
        vector<int> ord(N);
        iota(ord.begin(), ord.end(), 0);
        shuffle(ord.begin(), ord.end(), rng);
        vector<int> pos(N);
        for (int i = 0; i < N; ++i) pos[ord[i]] = i;

        // Orientation 1: edges go from higher pos to lower pos
        vector<int> qbits;
        vector<vector<U64>> reach;
        build_orientation_and_reach(pos, qbits, reach);

        int ans = ask_query(qbits);
        if (ans == -1) {
            // Fallback if no interactor; output any guess (0, 1) if possible
            int A = 0, B = (N >= 2 ? 1 : 0);
            cout << 1 << ' ' << A << ' ' << B << '\n';
            cout.flush();
            return 0;
        }
        used_queries++;
        if (ans == 1) {
            for (int a = 0; a < N; ++a) {
                bitset_and_inplace(cand[a], reach[a]);
                bitset_clearbit(cand[a], a);
            }
        } else {
            for (int a = 0; a < N; ++a) {
                bitset_andnot_inplace(cand[a], reach[a]);
                bitset_clearbit(cand[a], a);
            }
        }
        if (try_output_answer(cand)) return 0;

        if (used_queries + 1 > max_queries) break;

        // Orientation 2: reverse all edges (optional extra info)
        vector<int> qbits2(M);
        for (int i = 0; i < M; i++) qbits2[i] = 1 - qbits[i];

        // Build reachability for reversed orientation quickly:
        // Equivalent to use positions reversed: pos2[v] = N-1 - pos[v]
        vector<int> pos2(N);
        for (int v = 0; v < N; ++v) pos2[v] = N - 1 - pos[v];

        vector<vector<U64>> reach2;
        build_orientation_and_reach(pos2, qbits2, reach2);

        int ans2 = ask_query(qbits2);
        if (ans2 == -1) {
            int A = 0, B = (N >= 2 ? 1 : 0);
            cout << 1 << ' ' << A << ' ' << B << '\n';
            cout.flush();
            return 0;
        }
        used_queries++;
        if (ans2 == 1) {
            for (int a = 0; a < N; ++a) {
                bitset_and_inplace(cand[a], reach2[a]);
                bitset_clearbit(cand[a], a);
            }
        } else {
            for (int a = 0; a < N; ++a) {
                bitset_andnot_inplace(cand[a], reach2[a]);
                bitset_clearbit(cand[a], a);
            }
        }
        if (try_output_answer(cand)) return 0;
    }

    // If not uniquely determined, guess any remaining candidate pair
    if (!try_output_answer(cand)) {
        // Fallback: any pair (0, 1)
        int A = 0, B = (N >= 2 ? 1 : 0);
        cout << 1 << ' ' << A << ' ' << B << '\n';
        cout.flush();
    }
    return 0;
}