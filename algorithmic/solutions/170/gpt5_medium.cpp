#include <bits/stdc++.h>
using namespace std;

static inline void simulate(const vector<int>& a, const vector<int>& b, int N, int L, const vector<int>& T, vector<int>& t_out, long long& E_out) {
    t_out.assign(N, 0);
    vector<unsigned char> parity(N, 0);
    int cur = 0;
    for (int w = 0; w < L; ++w) {
        t_out[cur]++;
        parity[cur] ^= 1;
        if (w + 1 == L) break;
        cur = (parity[cur] ? a[cur] : b[cur]);
    }
    long long E = 0;
    for (int i = 0; i < N; ++i) {
        E += llabs((long long)t_out[i] - (long long)T[i]);
    }
    E_out = E;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, L;
    if (!(cin >> N >> L)) return 0;
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    vector<int> a(N), b(N);
    for (int i = 0; i < N; ++i) {
        a[i] = (i + 1) % N;
        b[i] = (i + 1) % N;
    }

    vector<int> t(N), best_t(N);
    long long E = 0, bestE = 0;
    simulate(a, b, N, L, T, t, E);
    bestE = E;
    best_t = t;

    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT_MS = 1800.0;

    vector<int> deficits(N);
    vector<int> cand_t(N);
    long long candE;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double, std::milli>(now - start_time).count();
        if (elapsed > TIME_LIMIT_MS) break;

        for (int i = 0; i < N; ++i) deficits[i] = T[i] - t[i];

        // Choose node r weighted by t[r] (skip nodes with t[r]==0)
        int r = -1;
        if (L > 0) {
            uniform_int_distribution<int> dist(0, L - 1);
            int pick = dist(rng);
            int acc = 0;
            for (int i = 0; i < N; ++i) {
                acc += t[i];
                if (pick < acc) { r = i; break; }
            }
        }
        if (r == -1) {
            uniform_int_distribution<int> distN(0, N - 1);
            r = distN(rng);
        }
        if (t[r] == 0) continue; // modifying this node won't affect anything

        // Determine which pointer to modify
        int odd_use = (t[r] + 1) / 2;
        int even_use = t[r] / 2;

        bool changeA;
        if (odd_use == 0) changeA = false;
        else if (even_use == 0) changeA = true;
        else {
            // Prefer to modify the pointer whose target is more oversubscribed (smaller deficit)
            int da = deficits[a[r]];
            int db = deficits[b[r]];
            changeA = (da <= db);
        }

        // Build candidate targets: top K positives by deficit
        const int K = 8;
        array<pair<int,int>, K> topPos; // (deficit, index)
        for (int k = 0; k < K; ++k) topPos[k] = make_pair(INT_MIN, -1);
        int bestNegIdx = 0; // index with largest deficit (closest to zero); initialize to 0
        for (int i = 0; i < N; ++i) {
            if (deficits[i] > 0) {
                // insert into top K
                pair<int,int> p = {deficits[i], i};
                for (int k = 0; k < K; ++k) {
                    if (p.first > topPos[k].first) {
                        for (int s = K - 1; s > k; --s) topPos[s] = topPos[s - 1];
                        topPos[k] = p;
                        break;
                    }
                }
            }
            if (deficits[i] > deficits[bestNegIdx]) bestNegIdx = i; // largest deficit (closest to zero, may be positive)
        }

        int y = -1;
        // If there is at least one positive deficit candidate
        if (topPos[0].second != -1) {
            // sample among positives with probability proportional to deficit
            int sumW = 0;
            for (int k = 0; k < K; ++k) {
                if (topPos[k].second == -1) break;
                sumW += topPos[k].first;
            }
            if (sumW <= 0) {
                y = topPos[0].second;
            } else {
                uniform_int_distribution<int> dist(1, sumW);
                int pick = dist(rng);
                int acc = 0;
                for (int k = 0; k < K; ++k) {
                    if (topPos[k].second == -1) break;
                    acc += topPos[k].first;
                    if (pick <= acc) { y = topPos[k].second; break; }
                }
                if (y == -1) y = topPos[0].second;
            }
        } else {
            // No positive deficits: choose index with largest deficit (closest to zero)
            y = bestNegIdx;
        }

        if (y == -1) continue;

        // If new target equals current, skip
        if (changeA) {
            if (a[r] == y) continue;
        } else {
            if (b[r] == y) continue;
        }

        int old = changeA ? a[r] : b[r];
        if (changeA) a[r] = y; else b[r] = y;

        simulate(a, b, N, L, T, cand_t, candE);
        if (candE <= bestE || candE < E) {
            // Accept if improved over current E; update current t and E
            t.swap(cand_t);
            E = candE;
            if (candE < bestE) {
                bestE = candE;
                best_t = t;
            }
        } else {
            // Revert
            if (changeA) a[r] = old; else b[r] = old;
        }
    }

    // Output final a and b
    for (int i = 0; i < N; ++i) {
        cout << a[i] << ' ' << b[i] << '\n';
    }
    return 0;
}