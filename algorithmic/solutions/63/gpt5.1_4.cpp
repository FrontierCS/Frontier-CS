#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<int> U(M), V(M);
    for (int i = 0; i < M; ++i) {
        cin >> U[i] >> V[i];
    }

    const int NB = (N + 63) / 64;
    const uint64_t FULL = ~0ULL;
    const uint64_t LAST_MASK = (N % 64 == 0) ? FULL : ((1ULL << (N % 64)) - 1);

    // Candidate pairs matrix: cand[u][v] == 1 means (u,v) still possible
    vector<uint64_t> cand((size_t)N * NB);
    for (int u = 0; u < N; ++u) {
        uint64_t *row = &cand[(size_t)u * NB];
        for (int b = 0; b < NB; ++b) row[b] = FULL;
        row[NB - 1] &= LAST_MASK;
        // remove diagonal element (u,u)
        row[u / 64] &= ~(1ULL << (u % 64));
    }

    auto countCandidates = [&](const vector<uint64_t> &mat) -> long long {
        long long cnt = 0;
        for (uint64_t w : mat) cnt += __builtin_popcountll(w);
        return cnt;
    };

    long long remaining = (long long)N * (N - 1);

    vector<vector<int>> out(N);
    vector<int> order(N), pos(N);
    vector<int> orient(M);
    vector<uint64_t> reach((size_t)N * NB);

    mt19937_64 rng(123456789);

    int maxQueries = 600;
    int qUsed = 0;

    while (remaining > 1 && qUsed < maxQueries) {
        // random permutation for DAG orientation
        for (int i = 0; i < N; ++i) order[i] = i;
        shuffle(order.begin(), order.end(), rng);
        for (int i = 0; i < N; ++i) pos[order[i]] = i;

        // build orientation and adjacency
        for (int u = 0; u < N; ++u) out[u].clear();
        for (int i = 0; i < M; ++i) {
            int a = U[i], b = V[i];
            if (pos[a] < pos[b]) {
                orient[i] = 1;
                out[a].push_back(b);
            } else {
                orient[i] = 0;
                out[b].push_back(a);
            }
        }

        // send query
        cout << 0;
        for (int i = 0; i < M; ++i) {
            cout << ' ' << orient[i];
        }
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) {
            return 0;
        }

        // compute reachability in DAG
        fill(reach.begin(), reach.end(), 0);
        for (int idx = N - 1; idx >= 0; --idx) {
            int u = order[idx];
            uint64_t *rowU = &reach[(size_t)u * NB];
            rowU[u / 64] |= (1ULL << (u % 64));
            for (int v : out[u]) {
                uint64_t *rowV = &reach[(size_t)v * NB];
                for (int b = 0; b < NB; ++b) {
                    rowU[b] |= rowV[b];
                }
            }
        }

        // update candidates based on answer x
        if (x == 1) {
            for (int u = 0; u < N; ++u) {
                uint64_t *rowC = &cand[(size_t)u * NB];
                uint64_t *rowR = &reach[(size_t)u * NB];
                for (int b = 0; b < NB; ++b) {
                    rowC[b] &= rowR[b];
                }
            }
        } else { // x == 0
            for (int u = 0; u < N; ++u) {
                uint64_t *rowC = &cand[(size_t)u * NB];
                uint64_t *rowR = &reach[(size_t)u * NB];
                for (int b = 0; b < NB; ++b) {
                    rowC[b] &= ~rowR[b];
                }
            }
        }

        // diagonal should already be zero; no need to fix explicitly

        remaining = countCandidates(cand);
        ++qUsed;
    }

    int A = -1, B = -1;
    if (remaining > 0) {
        for (int u = 0; u < N && A == -1; ++u) {
            uint64_t *row = &cand[(size_t)u * NB];
            for (int b = 0; b < NB && A == -1; ++b) {
                uint64_t w = row[b];
                while (w) {
                    int t = __builtin_ctzll(w);
                    int v = b * 64 + t;
                    if (v < N) {
                        A = u;
                        B = v;
                        break;
                    }
                    w &= w - 1;
                }
            }
        }
    }

    if (A == -1 || B == -1 || A == B) {
        // fallback (should be extremely unlikely)
        A = 0;
        B = (N > 1 ? 1 : 0);
    }

    cout << 1 << ' ' << A << ' ' << B << '\n';
    cout.flush();

    return 0;
}