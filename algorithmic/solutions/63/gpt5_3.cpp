#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<int> U(M), V(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        U[i] = u;
        V[i] = v;
    }

    int W = (N + 63) >> 6;
    vector<array<ull, 0>> dummy; // to satisfy some compilers

    // Initialize candidate masks: for each A, possible Bs
    vector<vector<ull>> cand(N, vector<ull>(W, ~0ull));
    // Mask to limit bits to first N
    vector<ull> FULLMASK(W, ~0ull);
    if (N % 64 != 0) {
        FULLMASK[W - 1] = (N % 64 == 0) ? ~0ull : ((1ull << (N % 64)) - 1ull);
    }
    for (int a = 0; a < N; ++a) {
        // Clear bit a (since A != B)
        int idx = a >> 6;
        int off = a & 63;
        cand[a][idx] &= ~(1ull << off);
        // Apply FULLMASK
        for (int k = 0; k < W; ++k) cand[a][k] &= FULLMASK[k];
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto compute_reach_and_orient = [&](const vector<int>& perm, vector<vector<int>>& out, vector<int>& orientBits, vector<vector<ull>>& dp) {
        out.assign(N, {});
        orientBits.assign(M, 0);
        // Build orientation based on permutation: edge goes from lower perm to higher perm
        for (int i = 0; i < M; ++i) {
            int u = U[i], v = V[i];
            if (perm[u] < perm[v]) {
                out[u].push_back(v);
                // 0 -> U_i to V_i
                orientBits[i] = 0;
            } else {
                out[v].push_back(u);
                // 1 -> V_i to U_i
                orientBits[i] = 1;
            }
        }
        // Compute reachability dp: dp[v] includes v itself
        dp.assign(N, vector<ull>(W, 0ull));
        vector<int> pos2v(N);
        for (int v = 0; v < N; ++v) pos2v[perm[v]] = v;
        for (int p = N - 1; p >= 0; --p) {
            int v = pos2v[p];
            vector<ull>& dv = dp[v];
            for (int w : out[v]) {
                vector<ull>& dw = dp[w];
                for (int k = 0; k < W; ++k) dv[k] |= dw[k];
            }
            // include self
            dv[v >> 6] |= (1ull << (v & 63));
            // mask
            for (int k = 0; k < W; ++k) dv[k] &= FULLMASK[k];
        }
    };

    auto update_candidates = [&](const vector<vector<ull>>& dp, int ans) {
        // Update cand[a] based on answer and dp[a] (dp includes self; we'll keep A!=B by clearing bit a again)
        if (ans == 1) {
            for (int a = 0; a < N; ++a) {
                const vector<ull>& da = dp[a];
                for (int k = 0; k < W; ++k) cand[a][k] &= da[k];
                // ensure A != B
                int idx = a >> 6, off = a & 63;
                cand[a][idx] &= ~(1ull << off);
            }
        } else {
            for (int a = 0; a < N; ++a) {
                for (int k = 0; k < W; ++k) cand[a][k] &= (~dp[a][k]) & FULLMASK[k];
                // ensure A != B
                int idx = a >> 6, off = a & 63;
                cand[a][idx] &= ~(1ull << off);
            }
        }
    };

    auto count_bits = [&](const vector<ull>& b) -> int {
        int c = 0;
        for (int k = 0; k < W; ++k) c += (int)__builtin_popcountll(b[k]);
        return c;
    };

    auto first_bit = [&](const vector<ull>& b) -> int {
        for (int k = 0; k < W; ++k) {
            if (b[k]) {
                int off = __builtin_ctzll(b[k]);
                return k * 64 + off;
            }
        }
        return -1;
    };

    auto find_unique_pair = [&]() -> pair<int,int> {
        int A = -1, B = -1, cnt = 0;
        for (int a = 0; a < N; ++a) {
            int c = count_bits(cand[a]);
            if (c == 1) {
                int b = first_bit(cand[a]);
                if (b != -1 && b != a) {
                    A = a; B = b; cnt++;
                    if (cnt > 1) return {-1, -1};
                }
            }
        }
        if (cnt == 1) return {A, B};
        return {-1, -1};
    };

    int maxQueries = 600;
    int asked = 0;
    while (asked < maxQueries) {
        // Generate random permutation
        vector<int> perm(N);
        iota(perm.begin(), perm.end(), 0);
        shuffle(perm.begin(), perm.end(), rng);

        // Prepare orientation and dp
        vector<vector<int>> out;
        vector<int> orientBits;
        vector<vector<ull>> dp;
        compute_reach_and_orient(perm, out, orientBits, dp);

        // Ask query
        cout << 0;
        for (int i = 0; i < M; ++i) {
            cout << ' ' << orientBits[i];
        }
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x != 0 && x != 1) return 0;

        update_candidates(dp, x);
        asked++;

        auto pr = find_unique_pair();
        if (pr.first != -1) {
            cout << 1 << ' ' << pr.first << ' ' << pr.second << '\n';
            cout.flush();
            return 0;
        }
    }

    // Fallback: if not uniquely identified, choose any remaining candidate
    for (int a = 0; a < N; ++a) {
        int c = count_bits(cand[a]);
        if (c >= 1) {
            int b = first_bit(cand[a]);
            if (b != -1 && b != a) {
                cout << 1 << ' ' << a << ' ' << b << '\n';
                cout.flush();
                return 0;
            }
        }
    }
    // As a last resort
    cout << 1 << ' ' << 0 << ' ' << 1 << '\n';
    cout.flush();
    return 0;
}