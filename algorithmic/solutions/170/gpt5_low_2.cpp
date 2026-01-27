#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long L;
    if (!(cin >> N >> L)) return 0;
    vector<long long> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    int M = 2 * N; // total edges
    // Adjust T for initial week at employee 0
    vector<long long> Tadj = T;
    if (Tadj[0] > 0) Tadj[0] -= 1;

    double factor = (double)(L - 1) / (double)M; // expected visits per indegree unit
    vector<double> k_real(N);
    vector<int> k(N);
    vector<double> frac(N);

    for (int i = 0; i < N; ++i) {
        k_real[i] = factor > 0 ? (double)Tadj[i] / factor : 1.0;
        double floorv = floor(k_real[i]);
        k[i] = max(1, (int)floorv);
        frac[i] = k_real[i] - floorv;
    }

    int S = 0;
    for (int i = 0; i < N; ++i) S += k[i];

    if (S < M) {
        vector<int> idx(N);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int a, int b){
            return frac[a] > frac[b];
        });
        int need = M - S;
        int p = 0;
        while (need > 0) {
            int i = idx[p % N];
            k[i] += 1;
            ++p;
            --need;
        }
    } else if (S > M) {
        vector<int> idx(N);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int a, int b){
            return frac[a] < frac[b];
        });
        int rem = S - M;
        int p = 0;
        while (rem > 0) {
            int i = idx[p % N];
            if (k[i] > 1) {
                k[i] -= 1;
                --rem;
            }
            ++p;
            // In worst case if many are at 1, keep cycling until enough reductions done
        }
    }

    // Build edges
    vector<int> a(N), b(N);
    // Ring edges as a_i
    for (int i = 0; i < N; ++i) {
        a[i] = (i + 1) % N;
    }
    // Remaining indegree needs after ring
    vector<int> need(N);
    int totalNeed = 0;
    for (int i = 0; i < N; ++i) {
        need[i] = max(0, k[i] - 1);
        totalNeed += need[i];
    }
    // totalNeed should be N
    if (totalNeed != N) {
        // Adjust to ensure sum equals N
        // If totalNeed < N, add to those with largest T; if > N, reduce from those with smallest T but keep >=0
        vector<int> idx(N);
        iota(idx.begin(), idx.end(), 0);
        if (totalNeed < N) {
            sort(idx.begin(), idx.end(), [&](int x, int y){ return T[x] > T[y]; });
            int add = N - totalNeed;
            int p = 0;
            while (add > 0) {
                int i = idx[p % N];
                need[i] += 1;
                ++p;
                --add;
            }
        } else {
            sort(idx.begin(), idx.end(), [&](int x, int y){ return T[x] < T[y]; });
            int rem = totalNeed - N;
            int p = 0;
            while (rem > 0) {
                int i = idx[p % N];
                if (need[i] > 0) {
                    need[i] -= 1;
                    --rem;
                }
                ++p;
            }
        }
        totalNeed = N;
    }

    int pv = 0;
    for (int i = 0; i < N; ++i) {
        while (pv < N && need[pv] == 0) ++pv;
        if (pv >= N) {
            // wrap around search
            pv = 0;
            while (pv < N && need[pv] == 0) ++pv;
        }
        if (pv >= N) {
            // fallback: point to next in ring (shouldn't happen if totalNeed == N)
            b[i] = (i + 1) % N;
        } else {
            b[i] = pv;
            need[pv]--;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << a[i] << " " << b[i] << "\n";
    }
    return 0;
}