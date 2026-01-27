#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    cin >> n;
    vector<vector<int>> D(n, vector<int>(n));
    vector<vector<int>> F(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> D[i][j];
        }
    }
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> F[i][j];
        }
    }

    // Initial heuristic: assign high-flow facilities to low-distance locations
    vector<int> flow(n, 0);
    vector<int> dist(n, 0);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            flow[i] += F[i][j] + F[j][i];
            dist[i] += D[i][j] + D[j][i];
        }
    }
    vector<int> fac_idx(n);
    iota(fac_idx.begin(), fac_idx.end(), 0);
    sort(fac_idx.begin(), fac_idx.end(), [&](int a, int b) {
        return flow[a] > flow[b];
    });
    vector<int> loc_idx(n);
    iota(loc_idx.begin(), loc_idx.end(), 0);
    sort(loc_idx.begin(), loc_idx.end(), [&](int a, int b) {
        return dist[a] < dist[b];
    });
    vector<int> p(n);
    vector<int> inv(n);
    for (int i = 0; i < n; i++) {
        int fac = fac_idx[i];
        int loc = loc_idx[i];
        p[fac] = loc;
        inv[loc] = fac;
    }

    // Compute initial cost
    long long cost = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cost += (long long)F[i][j] * D[p[i]][p[j]];
        }
    }

    // Simulated annealing
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> rand_real(0.0, 1.0);
    uniform_int_distribution<int> rand_int(0, n - 1);

    long long iterations = 200000;
    double temperature = 1.0;
    double cooling = 0.99999;

    for (long long iter = 0; iter < iterations; iter++) {
        int i = rand_int(rng);
        int j = rand_int(rng);
        while (j == i) j = rand_int(rng);

        int a = i, b = j;
        int x = p[a], y = p[b];
        long long delta = 0;

        for (int k = 0; k < n; k++) {
            if (k == a || k == b) continue;
            int pk = p[k];
            delta += F[a][k] * (D[y][pk] - D[x][pk]);
            delta += F[k][a] * (D[pk][y] - D[pk][x]);
            delta += F[b][k] * (D[x][pk] - D[y][pk]);
            delta += F[k][b] * (D[pk][x] - D[pk][y]);
        }
        delta += (F[a][b] - F[b][a]) * (D[y][x] - D[x][y]);

        if (delta < 0 || rand_real(rng) < exp(-delta / temperature)) {
            cost += delta;
            swap(p[a], p[b]);
            inv[x] = b;
            inv[y] = a;
        }
        temperature *= cooling;
    }

    // Output permutation (1‑based)
    for (int i = 0; i < n; i++) {
        cout << p[i] + 1 << (i == n - 1 ? '\n' : ' ');
    }
    return 0;
}