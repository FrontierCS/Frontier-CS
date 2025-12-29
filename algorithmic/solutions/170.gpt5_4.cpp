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

    long long q = L / (2LL * N); // Expected contribution per incoming edge

    // Decide how many b-incoming edges each node should get (k[i])
    vector<int> k(N, 0);
    for (int s = 0; s < N; ++s) {
        long long best_delta = LLONG_MIN;
        int best_i = 0;
        for (int i = 0; i < N; ++i) {
            long long P = q * (1 + k[i]);
            long long d1 = llabs(P - T[i]);
            long long d2 = llabs(P + q - T[i]);
            long long delta = d1 - d2; // improvement if we add one more b-edge to i
            if (delta > best_delta) {
                best_delta = delta;
                best_i = i;
            }
        }
        k[best_i]++;
    }

    // Build a ring for 'a' edges to ensure strong connectivity
    vector<int> a(N), b(N);
    for (int i = 0; i < N; ++i) a[i] = (i + 1) % N;

    // Assign 'b' edges according to counts k (each indicates needed b-incoming edges)
    vector<int> cnt = k; // cnt[j] is how many b-edges should point to j
    for (int u = 0; u < N; ++u) {
        int forb = a[u];
        int choose = -1;
        int maxcnt = -1;
        // Prefer destination not equal to a[u]
        for (int j = 0; j < N; ++j) {
            if (j == forb) continue;
            if (cnt[j] > maxcnt) {
                maxcnt = cnt[j];
                choose = j;
            }
        }
        if (choose == -1 || maxcnt == 0) {
            // If not possible, choose any with remaining count
            int idx = int(max_element(cnt.begin(), cnt.end()) - cnt.begin());
            choose = idx;
        }
        if (cnt[choose] == 0) {
            // Fallback (should rarely happen)
            choose = forb;
        }
        b[u] = choose;
        if (cnt[choose] > 0) cnt[choose]--;
    }

    for (int i = 0; i < N; ++i) {
        cout << a[i] << " " << b[i] << "\n";
    }
    return 0;
}